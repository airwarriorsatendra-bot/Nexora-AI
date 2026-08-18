"""Composition root for the Analytics vertical."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from src.analytics.repository import AnalyticsRepository
from src.analytics.service import AnalyticsService
from src.backlinks.repositories.backlink_repository import BacklinkRepository
from src.google_ads.repository import GoogleAdsRepository
from src.local_seo.repository import LocalSEORepository
from src.meta_ads.repository import MetaAdsRepository
from src.outreach.repositories.outreach_repository import OutreachAutomationRepository
from src.seo.repositories.seo_audit_repository import SEOAuditRepository
from src.search_console.repository import SearchConsoleRepository
from src.ga4.repository import GA4Repository


@dataclass(frozen=True, slots=True)
class AnalyticsSettings:
    database_path: Path

    @classmethod
    def from_environment(cls, environment: dict[str, str] | None = None) -> "AnalyticsSettings":
        values = environment if environment is not None else os.environ
        database_url = values.get("DATABASE_URL", "")
        if database_url.startswith("sqlite:///"):
            return cls(Path(database_url.removeprefix("sqlite:///")))
        if database_url:
            return cls(Path(database_url))
        return cls(Path(__file__).resolve().parents[2] / "storage" / "backlinks.db")


@dataclass(slots=True)
class AnalyticsApplication:
    service: AnalyticsService
    repository: AnalyticsRepository
    google_repository: GoogleAdsRepository
    meta_repository: MetaAdsRepository
    seo_repository: SEOAuditRepository
    backlink_repository: BacklinkRepository
    outreach_repository: OutreachAutomationRepository
    local_seo_repository: LocalSEORepository
    search_console_repository: SearchConsoleRepository
    ga4_repository: GA4Repository
    _closed: bool = False

    async def aclose(self) -> None:
        """Lifecycle hook kept idempotent for future managed dependencies."""
        self._closed = True


class AnalyticsComposition:
    def __init__(
        self,
        settings: AnalyticsSettings,
        *,
        analytics_repository_factory: Callable[[Path], AnalyticsRepository] = AnalyticsRepository,
        google_repository_factory: Callable[[Path], GoogleAdsRepository] = GoogleAdsRepository,
        meta_repository_factory: Callable[[Path], MetaAdsRepository] = MetaAdsRepository,
        seo_repository_factory: Callable[[Path], SEOAuditRepository] = SEOAuditRepository,
        backlink_repository_factory: Callable[[Path], BacklinkRepository] = BacklinkRepository,
        outreach_repository_factory: Callable[[Path], OutreachAutomationRepository] = OutreachAutomationRepository,
        local_seo_repository_factory: Callable[[Path], LocalSEORepository] = LocalSEORepository,
        search_console_repository_factory: Callable[[Path], SearchConsoleRepository] = SearchConsoleRepository,
        ga4_repository_factory: Callable[[Path], GA4Repository] = GA4Repository,
    ) -> None:
        self._settings = settings
        self._analytics_repository_factory = analytics_repository_factory
        self._google_repository_factory = google_repository_factory
        self._meta_repository_factory = meta_repository_factory
        self._seo_repository_factory = seo_repository_factory
        self._backlink_repository_factory = backlink_repository_factory
        self._outreach_repository_factory = outreach_repository_factory
        self._local_seo_repository_factory = local_seo_repository_factory
        self._search_console_repository_factory = search_console_repository_factory
        self._ga4_repository_factory = ga4_repository_factory

    def build(self) -> AnalyticsApplication:
        path = self._settings.database_path
        return AnalyticsApplication(
            service=AnalyticsService(),
            repository=self._analytics_repository_factory(path),
            google_repository=self._google_repository_factory(path),
            meta_repository=self._meta_repository_factory(path),
            seo_repository=self._seo_repository_factory(path),
            backlink_repository=self._backlink_repository_factory(path),
            outreach_repository=self._outreach_repository_factory(path),
            local_seo_repository=self._local_seo_repository_factory(path),
            search_console_repository=self._search_console_repository_factory(path),
            ga4_repository=self._ga4_repository_factory(path),
        )
