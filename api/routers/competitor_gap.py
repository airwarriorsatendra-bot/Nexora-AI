"""Persisted-only Competitor Gap workflow API."""

from fastapi import APIRouter, Query, Request

from src.competitor_gap.composition import CompetitorGapComposition, CompetitorGapSettings
from src.competitor_gap.domain import CompetitorGapReport

router = APIRouter(prefix="/competitor-gaps", tags=["competitor-gaps"])

async def _report(request: Request, target_domain: str) -> CompetitorGapReport:
    app = CompetitorGapComposition(CompetitorGapSettings(request.app.state.settings.database_path)).build()
    try: return await app.analyze(target_domain)
    finally: await app.aclose()

def _page(values, page: int, limit: int, sort_by: str, descending: bool):
    key = {"query": lambda value: getattr(value, "keyword", ""), "gap_type": lambda value: getattr(value, "gap_type", ""), "score": lambda value: getattr(getattr(value, "score", None), "total", 0), "observed_at": lambda value: getattr(value, "observed_at", "")}.get(sort_by, lambda value: getattr(value, "keyword", ""))
    ordered = sorted(values, key=key, reverse=descending)
    start = (page - 1) * limit
    return ordered[start:start + limit]


@router.get("/targets", response_model=list[str])
async def targets(request: Request) -> list[str]:
    app = CompetitorGapComposition(CompetitorGapSettings(request.app.state.settings.database_path)).build()
    try: return await app.targets()
    finally: await app.aclose()


@router.get("/report", response_model=CompetitorGapReport)
async def report(request: Request, target_domain: str = Query(min_length=1, max_length=253)) -> CompetitorGapReport:
    return await _report(request, target_domain)

@router.get("/competitors", response_model=list[dict])
async def competitors(request: Request, target_domain: str = Query(min_length=1, max_length=253), page: int = Query(1, ge=1), limit: int = Query(25, ge=1, le=100), descending: bool = False):
    report = await _report(request, target_domain)
    return [item.model_dump(mode="json") for item in _page(report.competitors, page, limit, "query", descending)]

@router.get("/keyword-gaps", response_model=list[dict])
async def keyword_gaps(request: Request, target_domain: str = Query(min_length=1, max_length=253), query: str | None = Query(None, max_length=256), gap_type: str | None = Query(None, max_length=64), priority: str | None = Query(None, max_length=16), sort_by: str = Query("query", pattern="^(query|gap_type|score)$"), page: int = Query(1, ge=1), limit: int = Query(25, ge=1, le=100), descending: bool = False):
    report = await _report(request, target_domain)
    values = [item for item in report.keyword_gaps if (query is None or query.casefold() in item.keyword.casefold()) and (gap_type is None or item.gap_type.value == gap_type) and (priority is None or item.priority.value == priority)]
    return [item.model_dump(mode="json") for item in _page(values, page, limit, sort_by, descending)]

@router.get("/page-gaps", response_model=list[dict])
async def page_gaps(request: Request, target_domain: str = Query(min_length=1, max_length=253), target_page: str | None = Query(None, max_length=2048), page: int = Query(1, ge=1), limit: int = Query(25, ge=1, le=100), descending: bool = False):
    report = await _report(request, target_domain)
    values = [item for item in report.page_gaps if target_page is None or target_page.casefold() in item.target_page.casefold()]
    return [item.model_dump(mode="json") for item in _page(values, page, limit, "query", descending)]

@router.get("/serp-detail", response_model=list[dict])
async def serp_detail(request: Request, target_domain: str = Query(min_length=1, max_length=253), query: str | None = Query(None, max_length=256), page: int = Query(1, ge=1), limit: int = Query(100, ge=1, le=500)):
    report = await _report(request, target_domain)
    rows = [{"query": gap.keyword, **row.model_dump(mode="json")} for gap in report.keyword_gaps for row in gap.serp if query is None or query.casefold() in gap.keyword.casefold()]
    start = (page - 1) * limit
    return rows[start:start + limit]

@router.get("/history", response_model=list[dict])
async def history(request: Request, target_domain: str = Query(min_length=1, max_length=253), page: int = Query(1, ge=1), limit: int = Query(25, ge=1, le=100)):
    report = await _report(request, target_domain)
    start = (page - 1) * limit
    return [item.model_dump(mode="json") for item in report.trends[start:start + limit]]
