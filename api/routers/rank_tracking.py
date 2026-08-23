"""Dedicated adapter for the existing Rank Tracking composition."""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from api.errors import APIError
from api.schemas.rank_tracking import AddTrackedKeywordRequest, RankCheckRequest, RankCheckResponse, RankRow, RankTrackingSnapshot
from src.rank_tracking.composition import RankTrackingApplication, RankTrackingComposition, RankTrackingSettings
from src.rank_tracking.domain import RankChange, RankCheck, TrackedKeyword, TrackingContext

router = APIRouter(prefix="/rank-tracking", tags=["rank-tracking"])


async def rank_application(request: Request) -> AsyncIterator[RankTrackingApplication]:
    environment = request.app.state.settings.environment_dict()
    environment["DATABASE_URL"] = str(request.app.state.settings.database_path)
    application = RankTrackingComposition(RankTrackingSettings.from_environment(environment)).build()
    try:
        yield application
    finally:
        await application.aclose()


@router.get("", response_model=RankTrackingSnapshot, summary="Read persisted tracked rankings")
async def snapshot(application: RankTrackingApplication = Depends(rank_application)) -> RankTrackingSnapshot:
    keywords = await application.repository.list_keywords()
    checks = {check.keyword_id: check for check in await application.repository.latest_checks()}
    rows: list[RankRow] = []
    for keyword in keywords:
        check = checks.get(keyword.keyword_id)
        change: RankChange | None = None
        if check is not None:
            history = await application.repository.history(keyword.keyword_id, keyword.context)
            previous = history[-2].target_position if len(history) > 1 else None
            change = application.service.change(previous, check.target_position, len(history) > 1)
        rows.append(RankRow(keyword=keyword, latest_check=check, change=change))
    return RankTrackingSnapshot(configured=application.settings.configured, rows=rows, competitors=list(await application.service.competitors()))


@router.get("/keywords", response_model=list[TrackedKeyword], summary="List persisted tracked keywords")
async def keywords(application: RankTrackingApplication = Depends(rank_application)) -> list[TrackedKeyword]:
    return list(await application.repository.list_keywords())


@router.post("/keywords", response_model=TrackedKeyword, status_code=status.HTTP_201_CREATED)
async def add_keyword(payload: AddTrackedKeywordRequest, application: RankTrackingApplication = Depends(rank_application)) -> TrackedKeyword:
    keyword = TrackedKeyword(keyword=payload.keyword, target_domain=payload.target_domain, target_url=payload.target_url, context=TrackingContext(country=payload.country, device=payload.device))
    return await application.service.add_keyword(keyword)


@router.get("/keywords/{keyword_id}/history", response_model=list[RankCheck])
async def history(keyword_id: UUID, application: RankTrackingApplication = Depends(rank_application)) -> list[RankCheck]:
    keyword = await application.repository.get_keyword(keyword_id)
    if keyword is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "NOT_FOUND", "Tracked keyword was not found.")
    return await application.repository.history(keyword.keyword_id, keyword.context)


@router.post("/check", response_model=RankCheckResponse)
async def check(payload: RankCheckRequest, application: RankTrackingApplication = Depends(rank_application)) -> RankCheckResponse:
    if not application.settings.configured:
        raise APIError(status.HTTP_409_CONFLICT, "PROVIDER_NOT_CONFIGURED", "Live rank checks are not configured.")
    outcomes = await application.service.check_active(payload.depth)
    return RankCheckResponse(checked=len(outcomes), results=[item[0] for item in outcomes])
