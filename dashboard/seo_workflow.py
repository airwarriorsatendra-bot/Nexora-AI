"""Dashboard adapter for the source-layer deterministic SEO audit."""

from __future__ import annotations

import os
from collections.abc import Callable

from dotenv import load_dotenv

from src.seo.composition import SEOComposition, SEOSettings
from src.seo.dto.seo_audit_request import SEOAuditRequest
from src.seo.dto.seo_audit_response import SEOAuditResponse
from src.seo.services.seo_audit_service import SEOAuditService


class SEODashboardWorkflow:
    """Keep Streamlit presentation separate from request mapping and service use."""

    def __init__(self, service_factory: Callable[[], SEOAuditService] | None = None) -> None:
        self._service_factory = service_factory or self._build_service

    async def execute(self, url: str) -> SEOAuditResponse:
        return await self._service_factory().audit(SEOAuditRequest(url=url))

    @staticmethod
    def _build_service() -> SEOAuditService:
        load_dotenv()
        settings = SEOSettings.from_environment(dict(os.environ))
        return SEOComposition(settings).build()
