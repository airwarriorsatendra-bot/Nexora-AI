"""Thin HTTP adapter for existing SEO workflows and repositories."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from api.config import APISettings
from api.schemas.pagination import PageMetadata
from api.schemas.seo import SEOAuditPage
from dashboard.seo_workflow import SEODashboardWorkflow
from src.seo.domain.seo_intelligence import SEOIntelligenceReport
from src.seo.dto.seo_audit_request import SEOAuditRequest
from src.seo.dto.seo_audit_response import SEOAuditResponse
from src.seo.repositories.seo_audit_repository import SEOAuditRepository

router = APIRouter(prefix="/seo", tags=["seo"])


def seo_workflow() -> SEODashboardWorkflow:
    return SEODashboardWorkflow()


def seo_repository(request: Request) -> SEOAuditRepository:
    settings: APISettings = request.app.state.settings
    return SEOAuditRepository(settings.database_path)


@router.get("/audits", response_model=SEOAuditPage, summary="List persisted SEO audits")
async def list_audits(
    page: int = Query(default=1, ge=1, le=10_000),
    limit: int = Query(default=25, ge=1, le=100),
    repository: SEOAuditRepository = Depends(seo_repository),
) -> SEOAuditPage:
    offset = (page - 1) * limit
    records = await repository.list_recent(limit=limit, offset=offset)
    items = records
    return SEOAuditPage(
        items=items,
        pagination=PageMetadata(
            page=page,
            limit=limit,
            returned=len(items),
            has_more=len(records) == limit,
        ),
    )


@router.post("/audits", response_model=SEOAuditResponse, summary="Run an explicit SEO audit")
async def run_audit(
    request: SEOAuditRequest,
    workflow: SEODashboardWorkflow = Depends(seo_workflow),
) -> SEOAuditResponse:
    return await workflow.execute(str(request.url))


@router.get(
    "/intelligence",
    response_model=SEOIntelligenceReport,
    summary="Analyze persisted GSC and GA4 SEO evidence",
)
async def intelligence(
    workflow: SEODashboardWorkflow = Depends(seo_workflow),
) -> SEOIntelligenceReport:
    return await workflow.intelligence()
