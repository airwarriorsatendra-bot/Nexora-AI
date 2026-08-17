"""Offline deterministic tests for the SEO audit service and repository."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from dashboard.seo_workflow import SEODashboardWorkflow
from src.core.exceptions import CrawlError, RepositoryError
from src.seo.dto.seo_audit_request import SEOAuditRequest
from src.seo.repositories.seo_audit_repository import SEOAuditRepository
from src.seo.services.seo_audit_service import SEOAuditService


VALID_HTML = """
<html lang="en"><head><title>Complete Fashion Guide for Sustainable Style</title>
<meta name="description" content="A practical sustainable fashion guide with useful advice for shoppers and modern brands everywhere.">
<link rel="canonical" href="https://example.com/guide">
<meta property="og:title" content="Fashion Guide"><meta name="twitter:card" content="summary">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Article"}</script></head>
<body><h1>Sustainable fashion guide</h1><h2>Materials</h2><p>""" + ("Useful detailed content. " * 100) + """</p>
<img src="hero.jpg" alt="Sustainable clothing"><a href="/about">About</a><a href="https://outside.example">External</a></body></html>
"""


class _RepositoryFailure:
    async def save(self, audit):
        del audit
        raise RepositoryError("storage unavailable")


class SEOAuditTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.repository = SEOAuditRepository(Path(self.directory.name) / "seo.db")

    async def asyncTearDown(self) -> None:
        self.directory.cleanup()

    def _service(self, html: str = VALID_HTML, error: Exception | None = None, repository=None) -> SEOAuditService:
        async def fetch(url: str) -> str:
            del url
            if error:
                raise error
            return html
        return SEOAuditService(fetch, repository or self.repository)

    async def test_valid_audit_persists_and_round_trips(self) -> None:
        service = self._service()
        response = await service.audit(SEOAuditRequest(url="https://example.com/guide"))
        self.assertTrue(response.success)
        assert response.audit is not None
        self.assertEqual(response.audit.metrics["h1_count"], 1)
        self.assertEqual(response.audit.metrics["schema_types"], "Article")
        stored = await self.repository.find_by_url("https://example.com/guide")
        self.assertEqual(stored, response.audit)

    def test_deterministic_scoring_and_core_on_page_findings(self) -> None:
        html = "<html><body><h1>One</h1><h1>Two</h1><img src='x'><a href='#'>Broken</a></body></html>"
        first = self._service(html).analyze_html("https://example.com", html)
        second = self._service(html).analyze_html("https://example.com", html)
        codes = {issue.code for issue in first.issues}
        self.assertEqual(first.category_scores, second.category_scores)
        self.assertIn("missing_title", codes)
        self.assertIn("missing_meta_description", codes)
        self.assertIn("multiple_h1", codes)
        self.assertIn("missing_canonical", codes)
        self.assertIn("missing_image_alt", codes)
        self.assertIn("invalid_internal_link", codes)

    def test_noindex_structured_data_and_empty_page_findings(self) -> None:
        html = """<html><head><meta name='robots' content='noindex'>
        <script type='application/ld+json'>{bad json}</script></head><body></body></html>"""
        audit = self._service(html).analyze_html("https://example.com", html)
        codes = {issue.code for issue in audit.issues}
        self.assertTrue({"noindex", "malformed_json_ld", "empty_page"}.issubset(codes))

    async def test_crawler_and_persistence_failures_are_safe(self) -> None:
        crawl_response = await self._service(error=CrawlError("unavailable")).audit(SEOAuditRequest(url="https://example.com"))
        self.assertFalse(crawl_response.success)
        persistence_response = await self._service(repository=_RepositoryFailure()).audit(SEOAuditRequest(url="https://example.com"))
        self.assertFalse(persistence_response.success)

    async def test_repeated_audit_is_idempotent_by_url(self) -> None:
        service = self._service()
        await service.audit(SEOAuditRequest(url="https://example.com"))
        await service.audit(SEOAuditRequest(url="https://example.com"))
        self.assertEqual(len(await self.repository.list_recent()), 1)

    async def test_dashboard_workflow_maps_url_to_injected_service(self) -> None:
        service = self._service()
        workflow = SEODashboardWorkflow(service_factory=lambda: service)
        response = await workflow.execute("https://example.com/guide")
        self.assertTrue(response.success)
        assert response.audit is not None
        self.assertEqual(str(response.audit.url), "https://example.com/guide")
