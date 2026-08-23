"""Persisted-only AEO/GEO readiness workflow API."""

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import PlainTextResponse
from api.errors import APIError
from api.schemas.aeo_geo import AEOGEOBriefRequest
from src.content_intelligence.composition import ContentIntelligenceComposition

from src.aeo_geo.composition import AEOGEOComposition
from src.aeo_geo.domain import AEOGEOReport
from src.competitor_gap.composition import CompetitorGapSettings

router = APIRouter(prefix="/aeo-geo", tags=["aeo-geo"])

async def _report(request: Request, target_domain: str) -> AEOGEOReport:
    app = AEOGEOComposition(CompetitorGapSettings(request.app.state.settings.database_path)).build()
    try: return await app.analyze(target_domain)
    finally: await app.aclose()


@router.get("/targets", response_model=list[str])
async def targets(request: Request) -> list[str]:
    app = AEOGEOComposition(CompetitorGapSettings(request.app.state.settings.database_path)).build()
    try: return await app.targets()
    finally: await app.aclose()


@router.get("/report", response_model=AEOGEOReport)
async def report(request: Request, target_domain: str = Query(min_length=1, max_length=253)) -> AEOGEOReport:
    return await _report(request, target_domain)

@router.get("/pages", response_model=list[dict])
async def pages(request: Request, target_domain: str = Query(min_length=1, max_length=253), page: int = Query(1, ge=1), limit: int = Query(25, ge=1, le=100)):
    value = (await _report(request, target_domain)).pages
    start = (page - 1) * limit
    return [item.model_dump(mode="json") for item in value[start:start + limit]]

@router.get("/questions", response_model=list[dict])
async def questions(request: Request, target_domain: str = Query(min_length=1, max_length=253), query: str | None = Query(None, max_length=256), page: int = Query(1, ge=1), limit: int = Query(25, ge=1, le=100)):
    value = [item for item in (await _report(request, target_domain)).questions if query is None or query.casefold() in item.query.casefold()]
    start = (page - 1) * limit
    return [item.model_dump(mode="json") for item in value[start:start + limit]]

@router.get("/entities", response_model=list[dict])
async def entities(request: Request, target_domain: str = Query(min_length=1, max_length=253)):
    report = await _report(request, target_domain)
    return [{"page": page.url, "structured_data_types": list(page.structured_data_types), "classification": "OBSERVED" if page.structured_data_types else "UNAVAILABLE"} for page in report.pages]

@router.get("/sources", response_model=dict)
async def sources() -> dict[str, str]:
    return {"status": "UNAVAILABLE", "message": "The persisted AEO/GEO crawl schema does not retain source URLs or source-quality evidence."}

@router.get("/recommendations", response_model=list[dict])
async def recommendations(request: Request, target_domain: str = Query(min_length=1, max_length=253)):
    report = await _report(request, target_domain)
    return [{"page": page.url, "recommendation": recommendation, "classification": "DERIVED"} for page in report.pages for recommendation in page.recommendations]

@router.get("/history", response_model=dict)
async def history() -> dict[str, str]:
    return {"status": "HISTORY_UNAVAILABLE", "message": "AEO/GEO reports are derived from current persisted evidence and are not versioned."}

@router.get("/export", response_class=PlainTextResponse)
async def export_report(request: Request, target_domain: str = Query(min_length=1, max_length=253)) -> str:
    from src.aeo_geo.service import AEOGEOService
    return AEOGEOService.markdown(await _report(request, target_domain))

@router.post("/brief", response_model=dict, status_code=status.HTTP_200_OK)
async def brief(payload: AEOGEOBriefRequest, request: Request):
    app = ContentIntelligenceComposition(CompetitorGapSettings(request.app.state.settings.database_path)).build()
    try:
        return (await app.generate(payload.target_domain, payload.query)).model_dump(mode="json")
    except StopIteration as error:
        raise APIError(status.HTTP_404_NOT_FOUND, "NOT_FOUND", "The AEO/GEO query is not available for content handoff.") from error
    finally: await app.aclose()
