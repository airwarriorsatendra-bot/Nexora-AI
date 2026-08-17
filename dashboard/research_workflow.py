"""Dashboard adapter for the locked asynchronous research application."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import pandas as pd
from dotenv import load_dotenv

from src.core.enums import ResearchMode, SearchProvider
from src.core.exceptions import ConfigurationError
from src.research.composition import (
    ResearchApplication,
    ResearchComposition,
    ResearchSettings,
)
from src.research.dto.request.research_options import ResearchOptions
from src.research.dto.request.research_request import ResearchRequest
from src.research.dto.response.research_response import ResearchResponse
from src.shared.value_objects.location import Location


SUPPORTED_SEARCH_PROVIDERS = (
    SearchProvider.TAVILY,
    SearchProvider.SERPER,
    SearchProvider.BRAVE,
    SearchProvider.GOOGLE_CSE,
    SearchProvider.PERPLEXITY,
)
SUPPORTED_AI_PROVIDERS = ("openai", "gemini", "groq", "claude", "nvidia")


@dataclass(frozen=True, slots=True)
class ResearchFormValues:
    """Validated dashboard inputs before they become a ResearchRequest."""

    industry: str
    research_mode: ResearchMode
    search_provider: SearchProvider
    ai_provider: str
    country: str
    state: str = ""
    city: str = ""
    max_results: int = 20
    custom_queries: tuple[str, ...] = ()
    included_domains: tuple[str, ...] = ()
    excluded_domains: tuple[str, ...] = ()
    enable_crawling: bool = True
    enable_ai_analysis: bool = True
    extract_contact_info: bool = True
    extract_social_links: bool = True
    include_subdomains: bool = False
    follow_redirects: bool = True


def split_lines(value: str) -> tuple[str, ...]:
    """Normalize textarea input without introducing another query parser."""
    return tuple(item.strip() for item in value.replace(",", "\n").splitlines() if item.strip())


def run_async(coroutine: Any) -> Any:
    """Run one bounded dashboard action without creating nested event loops."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)
    raise RuntimeError("Research cannot start while another event loop is active.")


class ResearchDashboardWorkflow:
    """Maps dashboard values to the existing research composition graph."""

    def __init__(
        self,
        *,
        settings_factory: Callable[..., ResearchSettings] = ResearchSettings.from_environment,
        composition_factory: Callable[[ResearchSettings], ResearchComposition] = ResearchComposition,
    ) -> None:
        self._settings_factory = settings_factory
        self._composition_factory = composition_factory

    def environment(self) -> Mapping[str, str]:
        """Load the existing environment mechanism without exposing credentials."""
        load_dotenv()
        return os.environ

    def available_search_providers(self) -> tuple[SearchProvider, ...]:
        environment = self.environment()
        return tuple(
            provider
            for provider in SUPPORTED_SEARCH_PROVIDERS
            if self._is_configured(environment, search_provider=provider)
        )

    def available_ai_providers(self) -> tuple[str, ...]:
        environment = self.environment()
        return tuple(
            provider
            for provider in SUPPORTED_AI_PROVIDERS
            if self._is_configured(environment, ai_provider=provider)
        )

    def build_request(self, values: ResearchFormValues) -> ResearchRequest:
        """Create the platform DTO used by ResearchService."""
        return ResearchRequest(
            industry=values.industry,
            research_mode=values.research_mode,
            provider=values.search_provider,
            location=Location(country=values.country, state=values.state, city=values.city),
            max_results=values.max_results,
            custom_queries=list(values.custom_queries),
            included_domains=list(values.included_domains),
            excluded_domains=list(values.excluded_domains),
            options=ResearchOptions(
                enable_crawling=values.enable_crawling,
                enable_ai_analysis=values.enable_ai_analysis,
                extract_contact_info=values.extract_contact_info,
                extract_social_links=values.extract_social_links,
                include_subdomains=values.include_subdomains,
                follow_redirects=values.follow_redirects,
            ),
        )

    async def execute(self, values: ResearchFormValues) -> ResearchResponse:
        """Execute one request and always close its composition-owned resources."""
        request = self.build_request(values)
        settings = self._settings_factory(
            search_provider=values.search_provider,
            ai_provider=values.ai_provider,
        )
        application = self._composition_factory(settings).build()
        try:
            return await application.research_service.start_research(request)
        finally:
            await application.aclose()

    async def list_persisted(self, values: ResearchFormValues) -> list[Any]:
        """Read the source-layer research table through its repository contract."""
        settings = self._settings_factory(
            search_provider=values.search_provider,
            ai_provider=values.ai_provider,
        )
        application: ResearchApplication = self._composition_factory(settings).build()
        try:
            return await application.prospect_repository.find_all()
        finally:
            await application.aclose()

    def _is_configured(
        self,
        environment: Mapping[str, str],
        *,
        search_provider: SearchProvider | None = None,
        ai_provider: str | None = None,
    ) -> bool:
        try:
            self._settings_factory(
                environment,
                search_provider=search_provider,
                ai_provider=ai_provider,
            )
        except ConfigurationError:
            return False
        return True


def prospects_to_dataframe(prospects: list[Any]) -> pd.DataFrame:
    """Serialize Research Prospect models for safe dashboard display and CSV export."""
    rows = [
        prospect.model_dump(mode="json")
        for prospect in prospects
    ]
    if not rows:
        return pd.DataFrame()
    dataframe = pd.DataFrame(rows)
    preferred_columns = [
        "domain", "url", "title", "category", "email", "phone", "ai_score",
        "guest_post_probability", "priority", "provider", "research_query",
    ]
    return dataframe[[column for column in preferred_columns if column in dataframe.columns]]
