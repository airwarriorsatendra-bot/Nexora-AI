"""Deterministic offline certification for bounded site crawl intelligence."""
from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from streamlit.testing.v1 import AppTest

from dashboard.site_crawl_workflow import SiteCrawlDashboardWorkflow
from src.core.exceptions import CrawlError
from src.research.services.crawler_service import CrawlerService
from src.site_crawl.composition import SiteCrawlComposition, SiteCrawlSettings
from src.site_crawl.crawler import BoundedSiteCrawler, FetchResult, SecurePageFetcher, normalize_url
from src.site_crawl.domain import SiteCrawlRequest


PAGES = {
    "https://example.test/": """<html><head><title>Example home page title</title><meta name='description' content='Home description'><link rel='canonical' href='/'></head><body><h1>Home</h1><a href='/category/'>Category</a><a href='/broken'>Broken</a><a href='/redirect'>Redirect</a><a href='mailto:x@example.test'>Mail</a></body></html>""",
    "https://example.test/category": """<html><head><title>Duplicate product title</title></head><body><h1>Products</h1><a href='/product-a#details'>Product A</a><a href='/product-b?color=red'>Product B</a></body></html>""",
    "https://example.test/product-a": """<html><head><title>Duplicate product title</title><meta name='robots' content='noindex'><link rel='canonical' href='/canonical-a'><script type='application/ld+json'>{"@type":"Product"}</script></head><body><h1>A</h1><h1>Extra</h1><img src='a.jpg'></body></html>""",
    "https://example.test/product-b?color=red": "<html><body><p>Thin product</p></body></html>",
    "https://example.test/final": "<html><head><title>Redirect target title</title></head><body><h1>Final</h1></body></html>",
}


class FixtureFetcher:
    def __init__(self, pages=None): self.pages = pages or PAGES; self.calls = []
    async def fetch(self, url, timeout):
        del timeout; self.calls.append(url)
        if url.endswith("/timeout"): return FetchResult(url,url,None,"","",{},error="Request timed out or was unreachable")
        if url.endswith("/broken"): return FetchResult(url,url,404,"text/html","<html><title>Missing</title></html>",{})
        if url.endswith("/server-error"): return FetchResult(url,url,500,"text/html","",{})
        if url.endswith("/redirect"):
            from src.site_crawl.domain import RedirectEdge
            return FetchResult(url,"https://example.test/final",200,"text/html",self.pages["https://example.test/final"],{},(RedirectEdge(source_url=url,target_url="https://example.test/final",status_code=301),))
        return FetchResult(url,url,200,"text/html",self.pages.get(url,"<html></html>"),{})


async def allow_fixture(url): return url


def render_fixture(workflow):
    from dashboard.site_crawl import render_site_crawl
    render_site_crawl(workflow)


class SiteCrawlTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory(); self.path = Path(self.directory.name)/"crawl.db"; self.fetcher = FixtureFetcher()
        self.crawler = BoundedSiteCrawler(self.fetcher.fetch, destination_validator=allow_fixture)
        self.app = SiteCrawlComposition(SiteCrawlSettings(self.path), crawler_factory=lambda:self.crawler, evidence_loader=lambda _:asyncio.sleep(0,result={})).build()
    async def asyncTearDown(self): await self.app.aclose(); self.directory.cleanup()

    def test_url_normalization_and_ssrf_regression(self):
        self.assertEqual(normalize_url("HTTPS://Example.COM:443/a/#x"),"https://example.com/a")
        self.assertEqual(normalize_url("https://example.com/a?b=2&a=1"),"https://example.com/a?b=2&a=1")
        self.assertNotEqual(normalize_url("https://example.com/a?x=1"),normalize_url("https://example.com/a?x=2"))
        for url in ("file:///etc/passwd","javascript:alert(1)","http://127.0.0.1/"):
            with self.assertRaises(CrawlError): CrawlerService._validate_url(url)

    async def test_redirect_to_private_address_is_blocked(self):
        client=httpx.AsyncClient(transport=httpx.MockTransport(lambda request:httpx.Response(302,headers={"location":"http://127.0.0.1/private"})))
        fetcher=SecurePageFetcher(client)
        with patch.object(CrawlerService,"_validate_destination",new=AsyncMock(side_effect=lambda url:url)):
            with self.assertRaises(CrawlError): await fetcher.fetch("https://example.test/",5)
        await client.aclose()

    async def test_bfs_depth_max_pages_and_duplicate_suppression(self):
        crawl = await self.app.service.run(SiteCrawlRequest(start_url="https://example.test/",max_pages=3,max_depth=2,max_concurrency=2))
        self.assertEqual([p.depth for p in crawl.pages],[0,1,1]); self.assertEqual(len(crawl.pages),3)
        self.assertEqual(len(self.fetcher.calls),len(set(self.fetcher.calls)))

    async def test_page_status_metadata_indexability_and_graph(self):
        crawl = await self.app.service.run(SiteCrawlRequest(start_url="https://example.test/",max_pages=10,max_depth=3))
        codes={i.code for i in crawl.issues}; self.assertTrue({"http_error","duplicate_title","multiple_h1","noindex_signal","missing_image_alt","thin_content_heuristic"} <= codes)
        product=next(p for p in crawl.pages if p.normalized_url.endswith("product-a")); self.assertEqual(product.indexability.value,"NON_INDEXABLE"); self.assertEqual(product.structured_data_types,("Product",))
        broken=next(link for link in crawl.links if link.target_url.endswith("/broken")); self.assertEqual(broken.target_status,404); self.assertEqual(broken.issue,"BROKEN_INTERNAL_LINK")
        redirected=next(link for link in crawl.links if link.target_url.endswith("/redirect")); self.assertEqual(redirected.issue,"LINKS_TO_REDIRECT")
        self.assertGreater(next(p for p in crawl.pages if p.normalized_url.endswith("product-a")).inlink_count,0)

    async def test_timeout_and_server_error_are_observations(self):
        pages={"https://example.test/":"<a href='/timeout'>T</a><a href='/server-error'>E</a>"}; fetcher=FixtureFetcher(pages); crawler=BoundedSiteCrawler(fetcher.fetch,destination_validator=allow_fixture)
        app=SiteCrawlComposition(SiteCrawlSettings(self.path),crawler_factory=lambda:crawler,evidence_loader=lambda _:asyncio.sleep(0,result={})).build()
        crawl=await app.service.run(SiteCrawlRequest(start_url="https://example.test/",max_pages=3,max_depth=1)); await app.aclose()
        self.assertIn(None,{p.status_code for p in crawl.pages}); self.assertIn(500,{p.status_code for p in crawl.pages})

    async def test_persistence_idempotency_concurrency_history_and_comparison(self):
        first=await self.app.service.run(SiteCrawlRequest(start_url="https://example.test/",max_pages=3,max_depth=1))
        await asyncio.gather(*(self.app.repository.save(first) for _ in range(4))); self.assertEqual(len(await self.app.repository.history()),1)
        second=await self.app.service.run(SiteCrawlRequest(start_url="https://example.test/",max_pages=5,max_depth=2)); history=await self.app.repository.history(); self.assertEqual(len(history),2)
        comparison=self.app.service.compare(second,first); self.assertTrue(comparison.new_pages)
        self.assertEqual((await self.app.repository.get(first.crawl_id)).crawl_id,first.crawl_id)

    async def test_gsc_ga4_rank_evidence_remains_distinct(self):
        evidence={"gsc":{"https://example.test/product-a":900},"ga4":{"https://example.test/product-a":42},"ranks":{"https://example.test/product-a":7}}
        app=SiteCrawlComposition(SiteCrawlSettings(self.path),crawler_factory=lambda:self.crawler,evidence_loader=lambda _:asyncio.sleep(0,result=evidence)).build()
        crawl=await app.service.run(SiteCrawlRequest(start_url="https://example.test/",max_pages=8,max_depth=3)); await app.aclose()
        item=next(o for o in crawl.opportunities if o.target_url.endswith("product-a")); joined=" ".join(item.evidence)
        self.assertIn("GSC impressions",joined); self.assertIn("GA4 sessions",joined); self.assertIn("Tracked SERP position",joined)

    async def test_dashboard_persisted_flow_exports_and_no_auto_crawl(self):
        await self.app.service.run(SiteCrawlRequest(start_url="https://example.test/",max_pages=5,max_depth=2))
        def factory(): return SiteCrawlComposition(SiteCrawlSettings(self.path),crawler_factory=lambda:BoundedSiteCrawler(lambda *_: (_ for _ in ()).throw(AssertionError("automatic crawl")),destination_validator=allow_fixture),evidence_loader=lambda _:asyncio.sleep(0,result={})).build()
        view=AppTest.from_function(render_fixture,args=(SiteCrawlDashboardWorkflow(factory=factory),)); view.run(timeout=30)
        self.assertFalse(view.exception); self.assertGreaterEqual(len(view.metric),10); self.assertGreaterEqual(len(view.download_button),5); self.assertTrue(view.dataframe)
