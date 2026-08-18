"""Explicit dependency composition for the asynchronous research application."""

from __future__ import annotations

import inspect
import logging
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.core.constants import (
    DEFAULT_NVIDIA_BASE_URL,
    ENV_AI_PROVIDER,
    ENV_BRAVE_API_KEY,
    ENV_CLAUDE_API_KEY,
    ENV_DATABASE_URL,
    ENV_GEMINI_API_KEY,
    ENV_GOOGLE_CSE_API_KEY,
    ENV_GOOGLE_CSE_ID,
    ENV_GROQ_API_KEY,
    ENV_NVIDIA_API_KEY,
    ENV_NVIDIA_BASE_URL,
    ENV_NVIDIA_MODEL,
    ENV_OPENAI_API_KEY,
    ENV_PERPLEXITY_API_KEY,
    ENV_SEARCH_PROVIDER,
    ENV_SERPER_API_KEY,
    ENV_TAVILY_API_KEY,
)
from src.core.enums import SearchProvider
from src.core.exceptions import ConfigurationError
from src.core.interfaces import IAIAnalysisService, ICrawlerService, IProspectRepository, IQueryGenerator, ISearchProvider
from src.research.providers.brave_provider import BraveProvider
from src.research.providers.google_cse_provider import GoogleCSEProvider
from src.research.providers.perplexity_provider import PerplexityProvider
from src.research.providers.serper_provider import SerperProvider
from src.research.providers.tavily_provider import TavilyProvider
from src.research.providers.claude_provider import ClaudeProvider
from src.research.providers.gemini_provider import GeminiProvider
from src.research.providers.groq_provider import GroqProvider
from src.research.providers.openai_provider import OpenAIProvider
from src.research.providers.nvidia_provider import NvidiaProvider
from src.research.repositories.prospect_repository import ProspectRepository
from src.research.services.ai_analysis_service import AIAnalysisService
from src.research.services.crawler_service import CrawlerService
from src.research.services.query_generator import QueryGenerator
from src.research.services.research_service import ResearchService

__all__ = ["ResearchApplication", "ResearchComposition", "ResearchSettings"]


@dataclass(frozen=True, slots=True)
class ResearchSettings:
    """Validated, immutable configuration for the research dependency graph."""

    database_path: Path
    search_provider: SearchProvider
    ai_provider: str
    search_api_key: str
    ai_api_key: str
    ai_model: str
    google_search_engine_id: str = ""
    nvidia_base_url: str = DEFAULT_NVIDIA_BASE_URL

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
        *,
        search_provider: SearchProvider | str | None = None,
        ai_provider: str | None = None,
    ) -> "ResearchSettings":
        if environment is None:
            load_dotenv()
            environment = os.environ

        selected_search_provider = (
            search_provider.value
            if isinstance(search_provider, SearchProvider)
            else search_provider
        )
        raw_search_provider = str(
            selected_search_provider
            or environment.get(ENV_SEARCH_PROVIDER, SearchProvider.TAVILY.value)
        ).strip().lower()
        try:
            search_provider = SearchProvider(raw_search_provider)
        except ValueError as exc:
            raise ConfigurationError(f"Unsupported SEARCH_PROVIDER: {raw_search_provider!r}.") from exc

        search_keys = {
            SearchProvider.TAVILY: ENV_TAVILY_API_KEY,
            SearchProvider.SERPER: ENV_SERPER_API_KEY,
            SearchProvider.BRAVE: ENV_BRAVE_API_KEY,
            SearchProvider.GOOGLE_CSE: ENV_GOOGLE_CSE_API_KEY,
            SearchProvider.PERPLEXITY: ENV_PERPLEXITY_API_KEY,
        }
        if search_provider not in search_keys:
            raise ConfigurationError(f"SEARCH_PROVIDER {search_provider.value!r} is not implemented.")
        search_api_key = environment.get(search_keys[search_provider], "").strip()
        if not search_api_key:
            raise ConfigurationError(f"{search_keys[search_provider]} is required for {search_provider.value}.")

        ai_provider = (ai_provider or environment.get(ENV_AI_PROVIDER, "openai")).strip().lower()
        ai_keys = {
            "openai": ENV_OPENAI_API_KEY,
            "gemini": ENV_GEMINI_API_KEY,
            "groq": ENV_GROQ_API_KEY,
            "nvidia": ENV_NVIDIA_API_KEY,
            "claude": ENV_CLAUDE_API_KEY,
        }
        if ai_provider not in ai_keys:
            raise ConfigurationError(f"AI_PROVIDER {ai_provider!r} is not implemented by the research layer.")
        ai_api_key = environment.get(ai_keys[ai_provider], "").strip()
        if not ai_api_key:
            raise ConfigurationError(f"{ai_keys[ai_provider]} is required for {ai_provider}.")

        models = {
            "openai": environment.get("OPENAI_MODEL", "gpt-4.1-mini"),
            "gemini": environment.get("GEMINI_MODEL", "gemini-2.0-flash"),
            "groq": environment.get("GROQ_MODEL", "openai/gpt-oss-120b"),
            "nvidia": environment.get(ENV_NVIDIA_MODEL, "meta/llama-3.3-70b-instruct"),
            "claude": environment.get("CLAUDE_MODEL", "claude-3-5-haiku-latest"),
        }
        google_search_engine_id = environment.get(ENV_GOOGLE_CSE_ID, "").strip()
        if search_provider is SearchProvider.GOOGLE_CSE and not google_search_engine_id:
            raise ConfigurationError(
                f"{ENV_GOOGLE_CSE_ID} is required for google_cse searches."
            )
        database_path = cls._database_path(environment.get(ENV_DATABASE_URL, ""))
        return cls(
            database_path=database_path,
            search_provider=search_provider,
            ai_provider=ai_provider,
            search_api_key=search_api_key,
            ai_api_key=ai_api_key,
            ai_model=models[ai_provider].strip(),
            google_search_engine_id=google_search_engine_id,
            nvidia_base_url=environment.get(
                ENV_NVIDIA_BASE_URL,
                DEFAULT_NVIDIA_BASE_URL,
            ).strip(),
        )

    @staticmethod
    def _database_path(value: str) -> Path:
        if not value.strip():
            return Path(__file__).resolve().parents[2] / "storage" / "backlinks.db"
        if value.startswith("sqlite:///"):
            return Path(value.removeprefix("sqlite:///"))
        if "://" in value:
            raise ConfigurationError("Research repositories support SQLite DATABASE_URL values only.")
        return Path(value)


@dataclass(slots=True)
class ResearchApplication:
    """Owns one fully constructed, replaceable research dependency graph."""

    settings: ResearchSettings
    research_service: ResearchService
    search_provider: ISearchProvider
    prospect_repository: IProspectRepository
    query_generator: IQueryGenerator
    crawler_service: ICrawlerService
    ai_analysis_service: IAIAnalysisService
    _closeables: tuple[Any, ...] = ()
    _closed: bool = False

    async def aclose(self) -> None:
        """Close any injected resources that expose a synchronous or async close hook."""
        if self._closed:
            return
        self._closed = True
        for dependency in reversed(self._closeables):
            close = getattr(dependency, "aclose", None) or getattr(dependency, "close", None)
            if callable(close):
                result = close()
                if inspect.isawaitable(result):
                    await result

    async def __aenter__(self) -> "ResearchApplication":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        await self.aclose()


class ResearchComposition:
    """Constructor-injected factory for the locked research architecture."""

    def __init__(
        self,
        settings: ResearchSettings,
        *,
        logger: logging.Logger | None = None,
        search_provider_factory: Callable[[ResearchSettings], ISearchProvider] | None = None,
        ai_provider_factory: Callable[[ResearchSettings], Any] | None = None,
        repository_factory: Callable[[Path], IProspectRepository] = ProspectRepository,
        query_generator_factory: Callable[[], IQueryGenerator] = QueryGenerator,
        crawler_service_factory: Callable[[], ICrawlerService] = CrawlerService,
        ai_analysis_service_factory: Callable[[Any], IAIAnalysisService] = AIAnalysisService,
        research_service_factory: Callable[..., ResearchService] = ResearchService,
    ) -> None:
        self._settings = settings
        self._logger = logger or logging.getLogger(__name__)
        self._search_provider_factory = search_provider_factory or self._build_search_provider
        self._ai_provider_factory = ai_provider_factory or self._build_ai_provider
        self._repository_factory = repository_factory
        self._query_generator_factory = query_generator_factory
        self._crawler_service_factory = crawler_service_factory
        self._ai_analysis_service_factory = ai_analysis_service_factory
        self._research_service_factory = research_service_factory

    def build(self) -> ResearchApplication:
        """Create a fresh dependency graph; no process-wide instances are retained."""
        search_provider = self._search_provider_factory(self._settings)
        ai_provider = self._ai_provider_factory(self._settings)
        repository = self._repository_factory(self._settings.database_path)
        query_generator = self._query_generator_factory()
        crawler_service = self._crawler_service_factory()
        ai_analysis_service = self._ai_analysis_service_factory(ai_provider)
        research_service = self._research_service_factory(
            query_generator=query_generator,
            search_provider=search_provider,
            crawler_service=crawler_service,
            ai_analysis_service=ai_analysis_service,
            prospect_repository=repository,
            logger=self._logger,
        )
        return ResearchApplication(
            settings=self._settings,
            research_service=research_service,
            search_provider=search_provider,
            prospect_repository=repository,
            query_generator=query_generator,
            crawler_service=crawler_service,
            ai_analysis_service=ai_analysis_service,
            _closeables=(
                search_provider,
                ai_provider,
                crawler_service,
                repository,
                research_service,
            ),
        )

    @staticmethod
    def _build_search_provider(settings: ResearchSettings) -> ISearchProvider:
        builders: dict[SearchProvider, Callable[[], ISearchProvider]] = {
            SearchProvider.TAVILY: lambda: TavilyProvider(settings.search_api_key),
            SearchProvider.SERPER: lambda: SerperProvider(settings.search_api_key),
            SearchProvider.BRAVE: lambda: BraveProvider(settings.search_api_key),
            SearchProvider.GOOGLE_CSE: lambda: GoogleCSEProvider(settings.search_api_key, settings.google_search_engine_id),
            SearchProvider.PERPLEXITY: lambda: PerplexityProvider(settings.search_api_key),
        }
        try:
            return builders[settings.search_provider]()
        except KeyError as exc:
            raise ConfigurationError(f"Search provider {settings.search_provider.value!r} is not implemented.") from exc

    @staticmethod
    def _build_ai_provider(settings: ResearchSettings) -> Any:
        builders: dict[str, Callable[[], Any]] = {
            "openai": lambda: OpenAIProvider(settings.ai_api_key, settings.ai_model),
            "gemini": lambda: GeminiProvider(settings.ai_api_key, settings.ai_model),
            "groq": lambda: GroqProvider(settings.ai_api_key, settings.ai_model),
            "nvidia": lambda: NvidiaProvider(
                settings.ai_api_key,
                settings.ai_model,
                base_url=settings.nvidia_base_url,
            ),
            "claude": lambda: ClaudeProvider(settings.ai_api_key, settings.ai_model),
        }
        try:
            return builders[settings.ai_provider]()
        except KeyError as exc:
            raise ConfigurationError(f"AI provider {settings.ai_provider!r} is not implemented.") from exc
