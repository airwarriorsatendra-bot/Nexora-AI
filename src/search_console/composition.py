"""Explicit composition and lifecycle ownership for Search Console."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from src.core.constants import ENV_DATABASE_URL, ENV_GSC_CLIENT_ID, ENV_GSC_CLIENT_SECRET, ENV_GSC_REFRESH_TOKEN
from src.search_console.providers.base import SearchConsoleProvider
from src.search_console.providers.google_provider import GoogleSearchConsoleProvider
from src.search_console.providers.offline_provider import UnconfiguredSearchConsoleProvider
from src.search_console.repository import SearchConsoleRepository
from src.search_console.service import SearchPerformanceService


@dataclass(frozen=True, slots=True)
class SearchConsoleSettings:
    database_path: Path
    client_id: str = ""
    client_secret: str = ""
    refresh_token: str = ""

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.refresh_token)

    @classmethod
    def from_environment(cls, environment: dict[str, str] | None = None) -> "SearchConsoleSettings":
        values = environment if environment is not None else os.environ
        database_url = values.get(ENV_DATABASE_URL, "")
        path = Path(database_url.removeprefix("sqlite:///")) if database_url.startswith("sqlite:///") else Path(database_url) if database_url else Path(__file__).resolve().parents[2] / "storage" / "backlinks.db"
        return cls(path, values.get(ENV_GSC_CLIENT_ID, ""), values.get(ENV_GSC_CLIENT_SECRET, ""), values.get(ENV_GSC_REFRESH_TOKEN, ""))


@dataclass(slots=True)
class SearchConsoleApplication:
    settings: SearchConsoleSettings
    provider: SearchConsoleProvider
    repository: SearchConsoleRepository
    service: SearchPerformanceService
    _closed: bool = False

    async def aclose(self) -> None:
        if not self._closed:
            await self.provider.aclose()
            self._closed = True


class SearchConsoleComposition:
    def __init__(self, settings: SearchConsoleSettings, *, provider_factory: Callable[[SearchConsoleSettings], SearchConsoleProvider] | None = None, repository_factory: Callable[[Path], SearchConsoleRepository] = SearchConsoleRepository) -> None:
        self._settings, self._provider_factory, self._repository_factory = settings, provider_factory, repository_factory

    def build(self) -> SearchConsoleApplication:
        provider = self._provider_factory(self._settings) if self._provider_factory else self._default_provider()
        repository = self._repository_factory(self._settings.database_path)
        return SearchConsoleApplication(self._settings, provider, repository, SearchPerformanceService(provider, repository))

    def _default_provider(self) -> SearchConsoleProvider:
        if not self._settings.configured:
            return UnconfiguredSearchConsoleProvider()
        return GoogleSearchConsoleProvider(client_id=self._settings.client_id, client_secret=self._settings.client_secret, refresh_token=self._settings.refresh_token)
