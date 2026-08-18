"""Composition root for persisted-only AEO/GEO readiness intelligence."""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from src.aeo_geo.service import AEOGEOService
from src.competitor_gap.composition import CompetitorGapApplication, CompetitorGapSettings


@dataclass(slots=True)
class AEOGEOApplication:
    settings: CompetitorGapSettings
    service: AEOGEOService
    gaps: CompetitorGapApplication

    async def targets(self) -> list[str]:
        return await self.gaps.targets()

    async def analyze(self, target: str):
        report = await self.gaps.analyze(target)
        host = self.service_host(target)
        history = await self.gaps.crawls.history(limit=500)
        compatible = [crawl for crawl in history if self.service_host(str(crawl.request.start_url)) == host]
        pages = {page.normalized_url: page for page in compatible[-1].pages} if compatible else {}
        return self.service.analyze(target, report, pages)

    async def aclose(self) -> None:
        await self.gaps.aclose()

    @staticmethod
    def service_host(value: str) -> str:
        candidate = value if "://" in value else f"https://{value}"
        return (urlsplit(candidate).hostname or "").casefold().removeprefix("www.")


class AEOGEOComposition:
    def __init__(self, settings: CompetitorGapSettings, service_factory=AEOGEOService) -> None:
        self.settings = settings
        self.service_factory = service_factory

    def build(self) -> AEOGEOApplication:
        return AEOGEOApplication(
            self.settings,
            self.service_factory(),
            CompetitorGapApplication(self.settings),
        )
