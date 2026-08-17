"""Integration tests for explicit research dependency composition."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from src.core.enums import ResearchMode, SearchProvider
from src.research.composition import ResearchComposition, ResearchSettings
from src.research.dto.request.research_options import ResearchOptions
from src.research.dto.request.research_request import ResearchRequest
from src.shared.value_objects.location import Location


class _FakeSearchProvider:
    provider_name = "fake-search"

    def __init__(self) -> None:
        self.closed = False

    async def search(self, query: str, max_results: int) -> list[dict[str, Any]]:
        del query, max_results
        return [{"url": "https://example.com", "title": "Example"}]

    async def aclose(self) -> None:
        self.closed = True


class _FakeCrawler:
    service_name = "FakeCrawler"

    def __init__(self) -> None:
        self.closed = False

    async def crawl(self, url: str) -> dict[str, Any]:
        del url
        return {"email": "editor@example.com"}

    async def aclose(self) -> None:
        self.closed = True


class _FakeAIProvider:
    def __init__(self) -> None:
        self.closed = False

    async def generate(self, prompt: str) -> str:
        del prompt
        return '{"ai_score": 80, "guest_post_probability": 75, "category": "fashion", "priority": "high", "summary": "good", "reason": "relevant"}'

    async def aclose(self) -> None:
        self.closed = True


class ResearchCompositionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.search_provider = _FakeSearchProvider()
        self.crawler = _FakeCrawler()
        self.ai_provider = _FakeAIProvider()
        self.settings = ResearchSettings(
            database_path=Path(self._temporary_directory.name) / "research.db",
            search_provider=SearchProvider.TAVILY,
            ai_provider="openai",
            search_api_key="test-search-key",
            ai_api_key="test-ai-key",
            ai_model="test-model",
        )

    async def asyncTearDown(self) -> None:
        self._temporary_directory.cleanup()

    async def test_wires_dependencies_and_executes_the_research_workflow(self) -> None:
        application = ResearchComposition(
            self.settings,
            search_provider_factory=lambda _: self.search_provider,
            ai_provider_factory=lambda _: self.ai_provider,
            crawler_service_factory=lambda: self.crawler,
        ).build()
        request = ResearchRequest(
            industry="Fashion",
            research_mode=ResearchMode.CUSTOM,
            location=Location(country="India"),
            custom_queries=["fashion guest posts"],
            max_results=1,
            options=ResearchOptions(enable_crawling=True, enable_ai_analysis=True),
        )

        response = await application.research_service.start_research(request)

        self.assertTrue(response.success)
        self.assertEqual(response.total_results, 1)
        self.assertEqual(response.results[0].domain, "example.com")
        self.assertEqual(response.results[0].ai_score, 80)
        self.assertEqual(len(await application.prospect_repository.find_all()), 1)

        await application.aclose()
        self.assertTrue(self.search_provider.closed)
        self.assertTrue(self.crawler.closed)
        self.assertTrue(self.ai_provider.closed)

    def test_reads_existing_environment_shape_without_global_state(self) -> None:
        settings = ResearchSettings.from_environment(
            {
                "SEARCH_PROVIDER": "tavily",
                "TAVILY_API_KEY": "search-key",
                "AI_PROVIDER": "openai",
                "OPENAI_API_KEY": "ai-key",
                "DATABASE_URL": "sqlite:///test.db",
            }
        )

        self.assertEqual(settings.search_provider, SearchProvider.TAVILY)
        self.assertEqual(settings.database_path, Path("test.db"))
