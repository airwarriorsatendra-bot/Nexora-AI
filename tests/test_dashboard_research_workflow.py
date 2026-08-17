"""Offline end-to-end tests for the dashboard Research adapter."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from dashboard.research_workflow import ResearchDashboardWorkflow, ResearchFormValues
from src.core.enums import ResearchMode, SearchProvider
from src.core.exceptions import ExternalAPIError, RepositoryError
from src.research.composition import ResearchComposition, ResearchSettings
from src.research.repositories.prospect_repository import ProspectRepository


class _SearchProvider:
    provider_name = "fake-search"

    def __init__(self, results: list[dict[str, Any]] | None = None, error: Exception | None = None) -> None:
        self.results = results or []
        self.error = error
        self.closed = False

    async def search(self, query: str, max_results: int) -> list[dict[str, Any]]:
        del query, max_results
        if self.error:
            raise self.error
        return self.results

    async def aclose(self) -> None:
        self.closed = True


class _Crawler:
    service_name = "FakeCrawler"

    def __init__(self) -> None:
        self.closed = False

    async def crawl(self, url: str) -> dict[str, Any]:
        del url
        return {"email": "editor@example.com"}

    async def aclose(self) -> None:
        self.closed = True


class _AIProvider:
    def __init__(self) -> None:
        self.closed = False

    async def generate(self, prompt: str) -> str:
        del prompt
        return '{"ai_score": 82, "guest_post_probability": 70, "category": "fashion", "priority": "high", "summary": "relevant", "reason": "good fit"}'

    async def aclose(self) -> None:
        self.closed = True


class _FailingRepository(ProspectRepository):
    async def save(self, prospect: Any) -> Any:
        del prospect
        raise RepositoryError("storage unavailable")


class DashboardResearchWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.settings = ResearchSettings(
            database_path=Path(self.temporary_directory.name) / "research.db",
            search_provider=SearchProvider.TAVILY,
            ai_provider="openai",
            search_api_key="search-key",
            ai_api_key="ai-key",
            ai_model="test-model",
        )

    async def asyncTearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _values(self) -> ResearchFormValues:
        return ResearchFormValues(
            industry="Fashion",
            research_mode=ResearchMode.CUSTOM,
            search_provider=SearchProvider.TAVILY,
            ai_provider="openai",
            country="India",
            custom_queries=("fashion guest posts",),
        )

    def _workflow(
        self,
        search: _SearchProvider,
        *,
        repository_factory: Any = ProspectRepository,
    ) -> tuple[ResearchDashboardWorkflow, _Crawler, _AIProvider]:
        crawler = _Crawler()
        ai_provider = _AIProvider()
        workflow = ResearchDashboardWorkflow(
            settings_factory=lambda *args, **kwargs: self.settings,
            composition_factory=lambda settings: ResearchComposition(
                settings,
                search_provider_factory=lambda _: search,
                ai_provider_factory=lambda _: ai_provider,
                crawler_service_factory=lambda: crawler,
                repository_factory=lambda path: repository_factory(path),
            ),
        )
        return workflow, crawler, ai_provider

    async def test_maps_executes_persists_and_closes_without_network(self) -> None:
        search = _SearchProvider([{"url": "https://example.com", "title": "Example"}])
        workflow, crawler, ai_provider = self._workflow(search)

        request = workflow.build_request(self._values())
        self.assertEqual(request.industry, "Fashion")
        self.assertEqual(request.provider, SearchProvider.TAVILY)
        self.assertEqual(request.custom_queries, ["fashion guest posts"])

        response = await workflow.execute(self._values())
        self.assertTrue(response.success)
        self.assertEqual(response.total_results, 1)
        self.assertEqual(response.results[0].email, "editor@example.com")
        self.assertTrue(search.closed)
        self.assertTrue(crawler.closed)
        self.assertTrue(ai_provider.closed)

        persisted = await workflow.list_persisted(self._values())
        self.assertEqual(len(persisted), 1)

    async def test_empty_and_provider_failure_flows_are_safe(self) -> None:
        empty_search = _SearchProvider()
        empty_workflow, _, _ = self._workflow(empty_search)
        empty_response = await empty_workflow.execute(self._values())
        self.assertTrue(empty_response.success)
        self.assertEqual(empty_response.total_results, 0)

        failed_search = _SearchProvider(error=ExternalAPIError("provider unavailable"))
        failed_workflow, _, _ = self._workflow(failed_search)
        failed_response = await failed_workflow.execute(self._values())
        self.assertTrue(failed_response.success)
        self.assertTrue(failed_response.warnings)
        self.assertTrue(failed_search.closed)

    async def test_persistence_failure_is_returned_without_resource_leaks(self) -> None:
        search = _SearchProvider([{"url": "https://example.org", "title": "Example"}])
        workflow, crawler, ai_provider = self._workflow(search, repository_factory=_FailingRepository)

        response = await workflow.execute(self._values())
        self.assertTrue(response.success)
        self.assertEqual(response.statistics.failed_websites, 1)
        self.assertTrue(response.warnings)
        self.assertTrue(search.closed)
        self.assertTrue(crawler.closed)
        self.assertTrue(ai_provider.closed)
