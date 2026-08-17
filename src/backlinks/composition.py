"""Explicit constructor composition for the Backlink Intelligence vertical."""

from __future__ import annotations

import inspect
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.backlinks.repositories.backlink_repository import BacklinkRepository
from src.backlinks.services.discovery_service import BacklinkDiscoveryService
from src.backlinks.services.verification_service import BacklinkVerificationService
from src.core.constants import ENV_DATABASE_URL
from src.core.exceptions import ConfigurationError
from src.research.services.crawler_service import CrawlerService


@dataclass(frozen=True, slots=True)
class BacklinkSettings:
    """Minimal immutable configuration for local backlink persistence."""

    database_path: Path

    @classmethod
    def from_environment(cls, environment: dict[str, str] | None = None) -> "BacklinkSettings":
        if environment is None:
            load_dotenv()
            environment = dict(os.environ)
        value = environment.get(ENV_DATABASE_URL, "").strip()
        if value.startswith("sqlite:///"):
            return cls(Path(value.removeprefix("sqlite:///")))
        if value and "://" in value:
            raise ConfigurationError("Backlink repositories support SQLite DATABASE_URL values only.")
        return cls(Path(value) if value else Path(__file__).resolve().parents[2] / "storage" / "backlinks.db")


@dataclass(slots=True)
class BacklinkApplication:
    """Fresh, closeable dependency graph for one Backlink workflow invocation."""

    discovery_service: BacklinkDiscoveryService
    verification_service: BacklinkVerificationService
    repository: BacklinkRepository
    _closeables: tuple[Any, ...] = ()
    _closed: bool = False

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        for dependency in reversed(self._closeables):
            close = getattr(dependency, "aclose", None) or getattr(dependency, "close", None)
            if callable(close):
                result = close()
                if inspect.isawaitable(result):
                    await result

    async def __aenter__(self) -> "BacklinkApplication":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        await self.aclose()


class BacklinkComposition:
    """Build replaceable services using the locked crawler and SQLite primitives."""

    def __init__(self, settings: BacklinkSettings, *, logger: logging.Logger | None = None, crawler_factory=CrawlerService, repository_factory=BacklinkRepository) -> None:
        self._settings = settings
        self._logger = logger or logging.getLogger(__name__)
        self._crawler_factory = crawler_factory
        self._repository_factory = repository_factory

    def build(self) -> BacklinkApplication:
        crawler = self._crawler_factory()
        repository = self._repository_factory(self._settings.database_path)
        return BacklinkApplication(
            discovery_service=BacklinkDiscoveryService(repository, self._logger),
            verification_service=BacklinkVerificationService(crawler.fetch_html, repository, self._logger),
            repository=repository,
            _closeables=(crawler, repository),
        )
