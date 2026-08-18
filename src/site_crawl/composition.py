"""Existing-style composition root for the SEO site-crawl graph."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin
from urllib.parse import urlsplit

from src.core.constants import ENV_DATABASE_URL
from src.ga4.domain import GA4Dimension
from src.ga4.repository import GA4Repository
from src.rank_tracking.repository import RankTrackingRepository
from src.search_console.domain import SearchDimension
from src.search_console.repository import SearchConsoleRepository
from src.site_crawl.crawler import BoundedSiteCrawler, SecurePageFetcher, normalize_url
from src.site_crawl.repository import SiteCrawlRepository
from src.site_crawl.service import SiteCrawlService


@dataclass(frozen=True, slots=True)
class SiteCrawlSettings:
    database_path: Path
    @classmethod
    def from_environment(cls, environment=None):
        values = environment if environment is not None else os.environ; raw = values.get(ENV_DATABASE_URL, "")
        return cls(Path(raw.removeprefix("sqlite:///")) if raw.startswith("sqlite:///") else Path(raw) if raw else Path(__file__).resolve().parents[2] / "storage" / "backlinks.db")


@dataclass(slots=True)
class SiteCrawlApplication:
    settings: SiteCrawlSettings
    repository: SiteCrawlRepository
    service: SiteCrawlService
    closed: bool = False
    async def aclose(self):
        if not self.closed: await self.service.aclose(); self.closed = True


class SiteCrawlComposition:
    def __init__(self, settings: SiteCrawlSettings, crawler_factory=None, repository_factory=SiteCrawlRepository, evidence_loader=None):
        self.settings, self.crawler_factory, self.repository_factory, self.evidence_loader = settings, crawler_factory, repository_factory, evidence_loader

    def build(self) -> SiteCrawlApplication:
        fetcher = None
        if self.crawler_factory: crawler = self.crawler_factory()
        else:
            fetcher = SecurePageFetcher(); crawler = BoundedSiteCrawler(fetcher.fetch, fetcher.aclose)
        repo = self.repository_factory(self.settings.database_path)
        loader = self.evidence_loader or self._evidence_loader(self.settings.database_path)
        return SiteCrawlApplication(self.settings, repo, SiteCrawlService(crawler, repo, loader))

    @staticmethod
    def _evidence_loader(path: Path):
        async def load(start_url: str):
            gsc_repo, ga4_repo, rank_repo = SearchConsoleRepository(path), GA4Repository(path), RankTrackingRepository(path)
            gsc_snapshot = await gsc_repo.latest(dimensions=(SearchDimension.PAGE,)); ga4_snapshot = await ga4_repo.latest((GA4Dimension.LANDING_PAGE,)); checks = await rank_repo.latest_checks()
            gsc, ga4, ranks = {}, {}, {}
            start_host = (urlsplit(start_url).hostname or "").lower().removeprefix("www.")
            gsc_matches_site = False
            if gsc_snapshot:
                property_value = gsc_snapshot.property.site_url.strip()
                if property_value.startswith("sc-domain:"):
                    property_host = property_value.removeprefix("sc-domain:").lower().removeprefix("www.")
                else:
                    property_host = (urlsplit(property_value).hostname or "").lower().removeprefix("www.")
                gsc_matches_site = property_host == start_host
            if gsc_snapshot and gsc_matches_site:
                for row in gsc_snapshot.records:
                    value = row.dimension_value(SearchDimension.PAGE)
                    if value:
                        try:
                            normalized = normalize_url(value)
                            if (urlsplit(normalized).hostname or "").lower().removeprefix("www.") == start_host:
                                gsc[normalized] = row.impressions
                        except Exception: pass
            if ga4_snapshot and gsc_matches_site:
                for row in ga4_snapshot.records:
                    if row.keys:
                        try: ga4[normalize_url(urljoin(start_url, row.keys[0]))] = int(row.metrics.get("sessions", 0))
                        except Exception: pass
            keywords = {item.keyword_id:item for item in await rank_repo.list_keywords()}
            for check in checks:
                item = keywords.get(check.keyword_id)
                if item and item.target_url and check.target_position is not None:
                    try:
                        normalized = normalize_url(item.target_url)
                        if (urlsplit(normalized).hostname or "").lower().removeprefix("www.") == start_host:
                            ranks[normalized] = check.target_position
                    except Exception: pass
            return {"gsc":gsc,"ga4":ga4,"ranks":ranks}
        return load
