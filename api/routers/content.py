"""Explicit deterministic current Content Intelligence API."""

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import PlainTextResponse

from api.errors import APIError
from api.schemas.content import ContentBriefRequest, ContentTarget, ContentTargetPage
from api.schemas.pagination import PageMetadata
from src.competitor_gap.composition import CompetitorGapSettings
from src.content_intelligence.composition import ContentIntelligenceComposition
from src.content_intelligence.domain import ContentBrief

router = APIRouter(prefix="/content", tags=["content"])


@router.get("/targets", response_model=list[ContentTarget])
async def targets(request: Request, query: str | None = Query(default=None, max_length=256), target_domain: str | None = Query(default=None, max_length=253), limit: int = Query(default=25, ge=1, le=100), offset: int = Query(default=0, ge=0)) -> list[ContentTarget]:
    app = ContentIntelligenceComposition(CompetitorGapSettings(request.app.state.settings.database_path)).build()
    try:
        values = [ContentTarget(target_domain=target, keyword=keyword, mapped_page=page) for target, keyword, page in await app.targets()]
        values = [item for item in values if (query is None or query.casefold() in item.keyword.casefold()) and (target_domain is None or item.target_domain.casefold() == target_domain.casefold())]
        return values[offset:offset + limit]
    finally: await app.aclose()

@router.get("/targets/page", response_model=ContentTargetPage)
async def target_page(request: Request, query: str | None = Query(default=None, max_length=256), target_domain: str | None = Query(default=None, max_length=253), page: int = Query(default=1, ge=1), limit: int = Query(default=25, ge=1, le=100)) -> ContentTargetPage:
    offset = (page - 1) * limit
    values = await targets(request, query, target_domain, 100, 0)
    items = values[offset:offset + limit]
    return ContentTargetPage(items=items, pagination=PageMetadata(page=page, limit=limit, returned=len(items), has_more=len(values) > offset + limit))


@router.post("/briefs", response_model=ContentBrief)
async def generate(payload: ContentBriefRequest, request: Request) -> ContentBrief:
    app = ContentIntelligenceComposition(CompetitorGapSettings(request.app.state.settings.database_path)).build()
    try:
        available = await app.targets()
        if not any(target == payload.target_domain and keyword == payload.keyword for target, keyword, _ in available):
            raise APIError(status.HTTP_404_NOT_FOUND, "NOT_FOUND", "Content target was not found.")
        return await app.generate(payload.target_domain, payload.keyword)
    finally: await app.aclose()

@router.get("/history")
async def history() -> dict[str, str]:
    return {"status": "HISTORY_UNAVAILABLE", "message": "Content briefs are derived on explicit request and are not persisted as versioned snapshots."}

@router.post("/briefs/markdown", response_class=PlainTextResponse)
async def markdown(payload: ContentBriefRequest, request: Request) -> str:
    app = ContentIntelligenceComposition(CompetitorGapSettings(request.app.state.settings.database_path)).build()
    try:
        available = await app.targets()
        if not any(target == payload.target_domain and keyword == payload.keyword for target, keyword, _ in available):
            raise APIError(status.HTTP_404_NOT_FOUND, "NOT_FOUND", "Content target was not found.")
        from src.content_intelligence.service import ContentIntelligenceService
        return ContentIntelligenceService.markdown(await app.generate(payload.target_domain, payload.keyword))
    finally: await app.aclose()
