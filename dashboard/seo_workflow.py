"""Dashboard adapters for deterministic technical and persisted SEO intelligence."""
from __future__ import annotations
import os
from collections.abc import Awaitable, Callable
from dotenv import load_dotenv
from src.ga4.domain import GA4Dimension
from src.ga4.repository import GA4Repository
from src.search_console.domain import SearchDimension, SearchPerformanceSnapshot
from src.search_console.repository import SearchConsoleRepository
from src.seo.composition import SEOComposition, SEOSettings
from src.seo.domain.seo_intelligence import SEOIntelligenceReport
from src.seo.dto.seo_audit_request import SEOAuditRequest
from src.seo.dto.seo_audit_response import SEOAuditResponse
from src.seo.services.seo_audit_service import SEOAuditService
from src.seo.services.seo_intelligence_service import SEOIntelligenceService


class SEODashboardWorkflow:
    def __init__(self, service_factory: Callable[[], SEOAuditService] | None = None, intelligence_factory: Callable[[], Awaitable[SEOIntelligenceReport]] | None = None) -> None:
        self._service_factory = service_factory or self._build_service
        self._intelligence_factory = intelligence_factory or self._build_intelligence

    async def execute(self, url: str) -> SEOAuditResponse:
        return await self._service_factory().audit(SEOAuditRequest(url=url))

    async def intelligence(self) -> SEOIntelligenceReport:
        return await self._intelligence_factory()

    @staticmethod
    def _previous(history: list[SearchPerformanceSnapshot], current: SearchPerformanceSnapshot | None) -> SearchPerformanceSnapshot | None:
        if current is None:
            return None
        candidates = [item for item in history if item.period.days == current.period.days and item.period.end_date < current.period.start_date]
        return candidates[-1] if candidates else None

    @staticmethod
    async def _build_intelligence() -> SEOIntelligenceReport:
        load_dotenv()
        settings = SEOSettings.from_environment(dict(os.environ))
        gsc, ga4 = SearchConsoleRepository(settings.database_path), GA4Repository(settings.database_path)
        queries = await gsc.latest(dimensions=(SearchDimension.QUERY,))
        pages = await gsc.latest(dimensions=(SearchDimension.PAGE,))
        query_history = await gsc.history(site_url=queries.property.site_url, dimensions=(SearchDimension.QUERY,)) if queries else []
        page_history = await gsc.history(site_url=pages.property.site_url, dimensions=(SearchDimension.PAGE,)) if pages else []
        return SEOIntelligenceService().analyze(current_queries=queries, current_pages=pages, previous_queries=SEODashboardWorkflow._previous(query_history, queries), previous_pages=SEODashboardWorkflow._previous(page_history, pages), ga4_landing_pages=await ga4.latest((GA4Dimension.LANDING_PAGE,)))

    @staticmethod
    def _build_service() -> SEOAuditService:
        load_dotenv()
        return SEOComposition(SEOSettings.from_environment(dict(os.environ))).build()
