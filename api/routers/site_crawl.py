"""Dedicated explicit-action adapter for bounded Site Crawl."""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from api.errors import APIError
from api.schemas.site_crawl import SiteCrawlDetail, SiteCrawlHistory
from src.site_crawl.composition import SiteCrawlApplication, SiteCrawlComposition, SiteCrawlSettings
from src.site_crawl.domain import SiteCrawl, SiteCrawlRequest
from src.site_crawl.repository import SiteCrawlRepository
from src.site_crawl.service import SiteCrawlService

router = APIRouter(prefix="/site-crawl", tags=["site-crawl"])


def repository(request: Request) -> SiteCrawlRepository:
    return SiteCrawlRepository(request.app.state.settings.database_path)


async def crawl_application(request: Request) -> AsyncIterator[SiteCrawlApplication]:
    application = SiteCrawlComposition(SiteCrawlSettings(request.app.state.settings.database_path)).build()
    try:
        yield application
    finally:
        await application.aclose()


@router.get("/runs", response_model=SiteCrawlHistory)
async def runs(start_url: str | None = Query(default=None, max_length=2048), limit: int = Query(default=25, ge=1, le=100), sort_by: str = Query(default="completed_at", pattern="^(completed_at|started_at|start_url)$"), descending: bool = False, store: SiteCrawlRepository = Depends(repository)) -> SiteCrawlHistory:
    items = await store.history(start_url, limit, sort_by, descending)
    latest = max(items, key=lambda item: item.completed_at) if items else None
    return SiteCrawlHistory(items=items, latest=latest)


@router.get("/runs/{crawl_id}", response_model=SiteCrawlDetail)
async def run_detail(crawl_id: UUID, page_issue: str | None = Query(default=None, max_length=100), issue_severity: str | None = Query(default=None, max_length=32), link_issue: str | None = Query(default=None, max_length=100), min_opportunity_priority: int | None = Query(default=None, ge=0, le=100), store: SiteCrawlRepository = Depends(repository)) -> SiteCrawlDetail:
    crawl = await store.get(crawl_id)
    if crawl is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "NOT_FOUND", "Site crawl was not found.")
    history = await store.history(str(crawl.request.start_url), 200)
    compatible = [item for item in history if item.crawl_id != crawl.crawl_id]
    filtered = crawl.model_copy(update={
        "pages": tuple(page for page in crawl.pages if page_issue is None or page_issue.casefold() in " ".join(page.issues).casefold()),
        "issues": tuple(issue for issue in crawl.issues if (issue_severity is None or issue.severity.casefold() == issue_severity.casefold()) and (page_issue is None or page_issue.casefold() in issue.code.casefold() or page_issue.casefold() in issue.evidence.casefold())),
        "links": tuple(link for link in crawl.links if link_issue is None or link_issue.casefold() in (link.issue or "").casefold()),
        "opportunities": tuple(opportunity for opportunity in crawl.opportunities if min_opportunity_priority is None or opportunity.priority >= min_opportunity_priority),
    })
    return SiteCrawlDetail(crawl=filtered, comparison=SiteCrawlService.compare(crawl, compatible[-1] if compatible else None))


@router.post("/runs", response_model=SiteCrawl, status_code=status.HTTP_201_CREATED)
async def start_run(payload: SiteCrawlRequest, application: SiteCrawlApplication = Depends(crawl_application)) -> SiteCrawl:
    return await application.service.run(payload)
