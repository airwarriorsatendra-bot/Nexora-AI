"""Offline contract tests for the Google Search Console vertical."""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import httpx
from streamlit.testing.v1 import AppTest

from dashboard.analytics_workflow import AnalyticsDashboardWorkflow
from dashboard.search_console_workflow import SearchConsoleDashboardWorkflow
from src.analytics.composition import AnalyticsApplication
from src.analytics.repository import AnalyticsRepository
from src.analytics.service import AnalyticsService
from src.core.exceptions import AuthenticationError, AuthorizationError, ExternalAPIError, SearchConsoleError
from src.search_console.composition import SearchConsoleComposition, SearchConsoleSettings
from src.search_console.domain import ReportingPeriod, SearchConsoleProperty, SearchDimension, SearchPerformanceRecord, SearchPerformanceSnapshot
from src.search_console.dto import SearchAnalyticsRequest
from src.search_console.providers.google_provider import GoogleSearchConsoleProvider
from src.search_console.providers.offline_provider import OfflineSearchConsoleProvider
from src.search_console.repository import SearchConsoleRepository
from src.search_console.service import SearchPerformanceService


PROPERTY = SearchConsoleProperty(site_url="https://example.com/", permission_level="siteOwner")
PERIOD = ReportingPeriod(start_date=date(2026, 8, 1), end_date=date(2026, 8, 28))


def record(key: str, clicks: int, impressions: int, ctr: str, position: str, dimension: SearchDimension = SearchDimension.QUERY) -> SearchPerformanceRecord:
    return SearchPerformanceRecord(dimensions=(dimension,), keys=(key,), clicks=clicks, impressions=impressions, ctr=Decimal(ctr), average_position=Decimal(position))


def configured_dashboard_page(workflow):
    from dashboard.search_console import render_search_console
    render_search_console(workflow)


class SearchConsoleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repository = SearchConsoleRepository(Path(self.tmp.name) / "gsc.db")

    async def asyncTearDown(self) -> None:
        self.tmp.cleanup()

    async def test_property_discovery_query_page_empty_and_normalization(self) -> None:
        query = (record("best shoes", 12, 120, "0.1", "8"),)
        page = (record("https://example.com/shoes", 8, 80, "0.1", "6", SearchDimension.PAGE),)
        provider = OfflineSearchConsoleProvider(properties=(PROPERTY,), records={(PROPERTY.site_url, ("query",)): query, (PROPERTY.site_url, ("page",)): page})
        service = SearchPerformanceService(provider, self.repository)
        self.assertEqual(await service.list_properties(), (PROPERTY,))
        self.assertEqual(await provider.query_search_analytics(SearchAnalyticsRequest(property=PROPERTY, period=PERIOD, dimensions=(SearchDimension.QUERY,))), query)
        self.assertEqual(await provider.query_search_analytics(SearchAnalyticsRequest(property=PROPERTY, period=PERIOD, dimensions=(SearchDimension.PAGE,))), page)
        self.assertEqual(await provider.query_search_analytics(SearchAnalyticsRequest(property=PROPERTY, period=PERIOD)), ())

    async def test_opportunities_comparison_and_invalid_dates(self) -> None:
        with self.assertRaises(ValueError):
            ReportingPeriod(start_date=PERIOD.end_date, end_date=PERIOD.start_date)
        records = (record("high low", 3, 500, "0.006", "9"), record("strong", 60, 500, "0.12", "3"), record("page two", 5, 500, "0.02", "14"), record("small", 1, 10, "0.1", "7"))
        self.assertEqual(SearchPerformanceService.ctr_opportunities(records)[0].keys, ("high low",))
        self.assertTrue(any(item.keys == ("page two",) for item in SearchPerformanceService.position_opportunities(records)))
        current = SearchPerformanceSnapshot(property=PROPERTY, period=PERIOD, dimensions=(SearchDimension.QUERY,), records=records)
        previous = current.model_copy(update={"period": ReportingPeriod(start_date=PERIOD.start_date - timedelta(days=28), end_date=PERIOD.end_date - timedelta(days=28))})
        self.assertIn("clicks", SearchPerformanceService.compare(current, previous))
        with self.assertRaises(SearchConsoleError):
            SearchPerformanceService.compare(current, current.model_copy(update={"dimensions": (SearchDimension.PAGE,)}))

    async def test_snapshot_persistence_concurrency_and_provenance(self) -> None:
        snapshot = SearchPerformanceSnapshot(property=PROPERTY, period=PERIOD, dimensions=(SearchDimension.QUERY,), records=(record("query", 1, 10, "0.1", "5"),))
        await asyncio.gather(*(self.repository.save(snapshot) for _ in range(8)))
        history = await self.repository.history(site_url=PROPERTY.site_url, dimensions=(SearchDimension.QUERY,))
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].source, "GOOGLE_SEARCH_CONSOLE")
        self.assertEqual(history[0].property.site_url, PROPERTY.site_url)
        self.assertEqual(await self.repository.latest(dimensions=(SearchDimension.QUERY,)), snapshot)

    async def test_refresh_persists_all_required_views_and_composition_close(self) -> None:
        aggregate = (SearchPerformanceRecord(clicks=10, impressions=100, ctr=Decimal("0.1"), average_position=Decimal("7")),)
        provider = OfflineSearchConsoleProvider(properties=(PROPERTY,), records={(PROPERTY.site_url, ()): aggregate, (PROPERTY.site_url, ("query",)): (record("q", 10, 100, "0.1", "7"),), (PROPERTY.site_url, ("page",)): (record("https://example.com", 10, 100, "0.1", "7", SearchDimension.PAGE),), (PROPERTY.site_url, ("date",)): (record("2026-08-01", 10, 100, "0.1", "7", SearchDimension.DATE),)})
        service = SearchPerformanceService(provider, self.repository)
        response = await service.refresh(property=PROPERTY, request=SearchAnalyticsRequest(property=PROPERTY, period=PERIOD))
        self.assertEqual(response.snapshot.totals.clicks, 10)
        self.assertEqual(len(await self.repository.history()), 4)
        composition = SearchConsoleComposition(SearchConsoleSettings(Path(self.tmp.name) / "composition.db"), provider_factory=lambda _: provider).build()
        await composition.aclose()
        await composition.aclose()
        self.assertTrue(provider.closed)

    async def test_analytics_preserves_organic_source_semantics(self) -> None:
        aggregate = SearchPerformanceSnapshot(property=PROPERTY, period=PERIOD, records=(SearchPerformanceRecord(clicks=10, impressions=100, ctr=Decimal("0.1"), average_position=Decimal("7")),))
        report = AnalyticsService().build(__import__("src.analytics.domain", fromlist=["Period"]).Period(date_from=PERIOD.start_date, date_to=PERIOD.end_date), search_console=aggregate)
        self.assertEqual({item.source_module for item in report.kpis}, {"GOOGLE_SEARCH_CONSOLE"})
        self.assertEqual({item.name for item in report.kpis}, {"organic_clicks", "organic_impressions", "organic_ctr", "organic_average_position"})

    async def test_google_provider_normalizes_retries_and_maps_failures(self) -> None:
        calls = {"query": 0}
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/token":
                return httpx.Response(200, json={"access_token": "test-token"})
            calls["query"] += 1
            if calls["query"] == 1:
                return httpx.Response(429, json={"error": "rate"})
            if request.url.path.endswith("/sites"):
                return httpx.Response(200, json={"siteEntry": [{"siteUrl": PROPERTY.site_url, "permissionLevel": "siteOwner"}]})
            return httpx.Response(200, json={"rows": [{"keys": ["q"], "clicks": 2, "impressions": 20, "ctr": 0.1, "position": 4.5}]})
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        provider = GoogleSearchConsoleProvider(client_id="id", client_secret="secret", refresh_token="refresh", http_client=client, token_url="https://oauth.test/token", api_base_url="https://api.test", max_retries=1)
        properties = await provider.list_properties()
        self.assertEqual(properties, (PROPERTY,))
        rows = await provider.query_search_analytics(SearchAnalyticsRequest(property=PROPERTY, period=PERIOD, dimensions=(SearchDimension.QUERY,)))
        self.assertEqual(rows[0].ctr, Decimal("0.1"))
        self.assertGreaterEqual(calls["query"], 3)
        await client.aclose()

    async def test_google_provider_auth_permission_transport_and_malformed_errors(self) -> None:
        async def assert_error(token_status: int, api_status: int, error: type[Exception]) -> None:
            def handler(request: httpx.Request) -> httpx.Response:
                if request.url.path == "/token":
                    return httpx.Response(token_status, json={"access_token": "token"} if token_status == 200 else {})
                return httpx.Response(api_status, json={})
            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            provider = GoogleSearchConsoleProvider(client_id="id", client_secret="secret", refresh_token="refresh", http_client=client, token_url="https://oauth.test/token", api_base_url="https://api.test", max_retries=0)
            with self.assertRaises(error):
                await provider.list_properties()
            await client.aclose()
        await assert_error(401, 200, AuthenticationError)
        await assert_error(200, 403, AuthorizationError)
        with self.assertRaises(AuthenticationError):
            GoogleSearchConsoleProvider(client_id="", client_secret="secret", refresh_token="refresh")
        def malformed(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"access_token": "token"} if request.url.path == "/token" else {"rows": [{"keys": [], "clicks": "bad"}]})
        client = httpx.AsyncClient(transport=httpx.MockTransport(malformed))
        provider = GoogleSearchConsoleProvider(client_id="id", client_secret="secret", refresh_token="refresh", http_client=client, token_url="https://oauth.test/token", api_base_url="https://api.test", max_retries=0)
        with self.assertRaises(ExternalAPIError):
            await provider.query_search_analytics(SearchAnalyticsRequest(property=PROPERTY, period=PERIOD, dimensions=(SearchDimension.QUERY,)))
        await client.aclose()


class SearchConsoleDashboardTests(unittest.TestCase):
    def test_unconfigured_dashboard_state_is_safe(self) -> None:
        with patch.dict("os.environ", {"GSC_CLIENT_ID": "", "GSC_CLIENT_SECRET": "", "GSC_REFRESH_TOKEN": ""}):
            app = AppTest.from_file("dashboard/app.py")
            app.session_state["nexora_navigation_page"] = "SEO"
            app.run(timeout=20)
            self.assertFalse(app.exception)
            self.assertTrue(any("Not configured" in markdown.value for markdown in app.markdown))

    def test_configured_fake_provider_dashboard_render_is_offline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            provider = OfflineSearchConsoleProvider(properties=(PROPERTY,))
            application = SearchConsoleComposition(
                SearchConsoleSettings(Path(directory) / "dashboard.db", "id", "secret", "refresh"),
                provider_factory=lambda _: provider,
            ).build()
            workflow = SearchConsoleDashboardWorkflow(factory=lambda: application)
            app = AppTest.from_function(configured_dashboard_page, args=(workflow,))
            app.run(timeout=20)
            self.assertFalse(app.exception)
            self.assertTrue(any(button.key == "gsc-discover" for button in app.button))
            next(button for button in app.button if button.key == "gsc-discover").click()
            app.run(timeout=20)
            self.assertFalse(app.exception)
            self.assertTrue(any(selectbox.label == "Property" for selectbox in app.selectbox))
