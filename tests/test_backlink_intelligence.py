"""Offline deterministic tests for the Backlink Intelligence vertical."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from dashboard.backlinks_workflow import BacklinksDashboardWorkflow, backlinks_to_dataframe
from src.backlinks.composition import BacklinkComposition, BacklinkSettings
from src.backlinks.dto.backlink_discovery import BacklinkDiscoveryRequest
from src.backlinks.dto.backlink_verification import BacklinkVerificationRequest
from src.backlinks.repositories.backlink_repository import BacklinkRepository
from src.backlinks.services.discovery_service import BacklinkDiscoveryService
from src.backlinks.services.verification_service import BacklinkVerificationService
from src.core.enums import BacklinkVerificationStatus, LinkAttribute
from src.core.exceptions import CrawlError


LINK_HTML = """<html><body><a href='https://example.com/guide' rel='nofollow sponsored ugc'>Example Guide</a></body></html>"""


class _Crawler:
    def __init__(self, html: str = LINK_HTML, error: Exception | None = None) -> None:
        self.html, self.error, self.closed = html, error, False

    async def fetch_html(self, url: str) -> str:
        del url
        if self.error:
            raise self.error
        return self.html

    async def aclose(self) -> None:
        self.closed = True


class BacklinkIntelligenceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.repository = BacklinkRepository(Path(self.directory.name) / "backlinks.db")

    async def asyncTearDown(self) -> None:
        self.directory.cleanup()

    async def test_discovery_is_idempotent_and_keeps_opportunities_separate(self) -> None:
        service = BacklinkDiscoveryService(self.repository)
        request = BacklinkDiscoveryRequest(target_url="https://example.com/guide", candidate_urls=["https://publisher.example/write-for-us"])
        first, second = await service.discover(request), await service.discover(request)
        self.assertTrue(first.success and second.success)
        stored = await self.repository.list_opportunities(domain="publisher.example")
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0].opportunity_type.value, "guest_post")
        self.assertEqual(await self.repository.list_backlinks(target_domain="example.com"), [])

    async def test_verification_parses_anchor_and_observable_rel_attributes(self) -> None:
        service = BacklinkVerificationService(_Crawler().fetch_html, self.repository)
        response = await service.verify(BacklinkVerificationRequest(source_url="https://publisher.example/post#part", target_url="https://example.com/guide"))
        self.assertTrue(response.success)
        assert response.backlink is not None
        self.assertEqual(response.backlink.anchor_text, "Example Guide")
        self.assertEqual(set(response.backlink.rel), {LinkAttribute.NOFOLLOW, LinkAttribute.SPONSORED, LinkAttribute.UGC})
        self.assertEqual(response.backlink.status, BacklinkVerificationStatus.VERIFIED)
        loaded = await self.repository.find_by_identity("https://publisher.example/post", "https://example.com/guide")
        self.assertEqual(loaded, response.backlink)

    async def test_missing_link_marks_only_previously_verified_link_lost(self) -> None:
        request = BacklinkVerificationRequest(source_url="https://publisher.example/post", target_url="https://example.com/guide")
        service = BacklinkVerificationService(_Crawler().fetch_html, self.repository)
        await service.verify(request)
        missing = await BacklinkVerificationService(_Crawler("<html><body>gone</body></html>").fetch_html, self.repository).verify(request)
        assert missing.backlink is not None
        self.assertEqual(missing.backlink.status, BacklinkVerificationStatus.LOST)

        other = await BacklinkVerificationService(_Crawler("<html></html>").fetch_html, self.repository).verify(BacklinkVerificationRequest(source_url="https://other.example", target_url="https://example.com/guide"))
        assert other.backlink is not None
        self.assertEqual(other.backlink.status, BacklinkVerificationStatus.DISCOVERED)

    async def test_crawl_failure_preserves_a_previously_verified_link(self) -> None:
        request = BacklinkVerificationRequest(source_url="https://publisher.example/post", target_url="https://example.com/guide")
        await BacklinkVerificationService(_Crawler().fetch_html, self.repository).verify(request)
        response = await BacklinkVerificationService(_Crawler(error=CrawlError("offline")).fetch_html, self.repository).verify(request)
        self.assertFalse(response.success)
        assert response.backlink is not None
        self.assertEqual(response.backlink.status, BacklinkVerificationStatus.VERIFIED)

    async def test_repository_filtering_pagination_bulk_and_referring_domains(self) -> None:
        service = BacklinkVerificationService(_Crawler().fetch_html, self.repository)
        for source in ("https://one.example/a", "https://two.example/a"):
            await service.verify(BacklinkVerificationRequest(source_url=source, target_url="https://example.com/guide"))
        self.assertEqual(len(await self.repository.list_backlinks(target_domain="example.com", limit=1)), 1)
        self.assertEqual(len(await self.repository.list_backlinks(status=BacklinkVerificationStatus.VERIFIED, limit=10)), 2)
        domains = await self.repository.referring_domains("example.com")
        self.assertEqual({row["source_domain"] for row in domains}, {"one.example", "two.example"})

    async def test_composition_dashboard_workflow_export_and_close(self) -> None:
        crawler = _Crawler()
        application = BacklinkComposition(BacklinkSettings(Path(self.directory.name) / "composition.db"), crawler_factory=lambda: crawler).build()
        response = await application.verification_service.verify(BacklinkVerificationRequest(source_url="https://publisher.example/post", target_url="https://example.com/guide"))
        self.assertTrue(response.success)
        await application.aclose()
        self.assertTrue(crawler.closed)

        workflow = BacklinksDashboardWorkflow(application_factory=lambda: BacklinkComposition(BacklinkSettings(Path(self.directory.name) / "workflow.db"), crawler_factory=_Crawler).build())
        discovered = await workflow.discover("https://example.com/guide", ["https://publisher.example/resources"])
        self.assertTrue(discovered.success)
        verified = await workflow.verify("https://publisher.example/post", "https://example.com/guide")
        self.assertTrue(verified.success)
        links = await workflow.list_backlinks("example.com")
        self.assertIn("source_url", backlinks_to_dataframe(links).columns)
