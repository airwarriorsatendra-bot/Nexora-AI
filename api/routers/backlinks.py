"""Read-only adapter for persisted Backlink Intelligence evidence."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request, status

from api.config import APISettings
from api.errors import APIError
from api.schemas.backlinks import AuthorityPreviewResponse, AuthorityRequest, BacklinkSnapshot
from src.backlinks.composition import BacklinkComposition, BacklinkSettings
from src.backlinks.domain import AuthorityObservation
from src.backlinks.domain.intelligence import AuthorityScope
from src.backlinks.services.intelligence_service import BacklinkIntelligenceService
from src.backlinks.repositories.backlink_repository import BacklinkRepository
from src.core.constants import ENV_MOZ_API_TOKEN

router = APIRouter(prefix="/backlinks", tags=["backlinks"])

async def _repository(request: Request) -> BacklinkRepository:
    return BacklinkRepository(request.app.state.settings.database_path)

def _slice(values, page: int, limit: int):
    start = (page - 1) * limit
    return values[start:start + limit]


@router.get("", response_model=BacklinkSnapshot, summary="Read persisted backlink intelligence")
async def snapshot(
    request: Request,
    target_domain: str | None = Query(default=None, min_length=1, max_length=253),
) -> BacklinkSnapshot:
    settings: APISettings = request.app.state.settings
    repository = BacklinkRepository(settings.database_path)
    backlinks = await repository.list_backlinks(target_domain=target_domain, limit=500)
    opportunities = await repository.list_opportunities(domain=target_domain, limit=500)
    authority = await repository.authority_history(target=target_domain, limit=500)
    prospects = await repository.list_prospects(limit=500)
    prospect_history = await repository.prospect_history(limit=500)
    referring_domains = await repository.referring_domains(target_domain) if target_domain else []
    intersect = []
    anchors = list(BacklinkIntelligenceService.anchor_summary(backlinks))
    reclamation = list(BacklinkIntelligenceService.reclamation(backlinks, {}))
    return BacklinkSnapshot(
        backlinks=backlinks,
        opportunities=opportunities,
        authority=authority,
        prospects=prospects,
        referring_domains=referring_domains,
        prospect_history=prospect_history,
        intersect=intersect,
        competitor_gaps=intersect,
        anchors=anchors,
        reclamation=reclamation,
        moz_configured=bool(settings.environment_dict().get(ENV_MOZ_API_TOKEN, "").strip()),
    )

@router.get("/profile", response_model=list[dict])
async def profile(request: Request, target_domain: str | None = Query(None, max_length=253), source_domain: str | None = Query(None, max_length=253), state: str | None = Query(None, max_length=32), page: int = Query(1, ge=1), limit: int = Query(25, ge=1, le=100)):
    repository = await _repository(request)
    from src.core.enums import BacklinkVerificationStatus
    try: status_filter = BacklinkVerificationStatus(state) if state else None
    except ValueError as error: raise APIError(status.HTTP_422_UNPROCESSABLE_CONTENT, "INVALID_STATE", "The backlink state is invalid.") from error
    values = await repository.list_backlinks(target_domain=target_domain, source_domain=source_domain, status=status_filter, limit=limit, offset=(page - 1) * limit)
    return [item.model_dump(mode="json") for item in values]

@router.get("/referring-domains", response_model=list[dict])
async def referring_domains(request: Request, target_domain: str = Query(min_length=1, max_length=253), page: int = Query(1, ge=1), limit: int = Query(25, ge=1, le=100)):
    values = (await (await _repository(request)).referring_domains(target_domain))
    return _slice(values, page, limit)

@router.get("/authority", response_model=list[AuthorityObservation])
async def authority(request: Request, target: str | None = Query(None, max_length=2048), page: int = Query(1, ge=1), limit: int = Query(25, ge=1, le=100)):
    values = await (await _repository(request)).authority_history(target=target, limit=500)
    return _slice(values, page, limit)

@router.get("/prospects", response_model=list[dict])
async def prospects(request: Request, page: int = Query(1, ge=1), limit: int = Query(25, ge=1, le=100)):
    values = await (await _repository(request)).list_prospects(limit=500)
    return [item.model_dump(mode="json") for item in _slice(values, page, limit)]

@router.get("/reclamation", response_model=list[dict])
async def reclamation(request: Request, target_domain: str | None = Query(None, max_length=253), page: int = Query(1, ge=1), limit: int = Query(25, ge=1, le=100)):
    repository = await _repository(request)
    values = await repository.list_backlinks(target_domain=target_domain, limit=500)
    return _slice(list(BacklinkIntelligenceService.reclamation(values, {})), page, limit)

@router.get("/history", response_model=list[dict])
async def history(request: Request, page: int = Query(1, ge=1), limit: int = Query(25, ge=1, le=100)):
    values = await (await _repository(request)).prospect_history(limit=500)
    return [item.model_dump(mode="json") for item in _slice(values, page, limit)]


def _application(request: Request):
    environment = request.app.state.settings.environment_dict()
    environment["DATABASE_URL"] = str(request.app.state.settings.database_path)
    return BacklinkComposition(BacklinkSettings.from_environment(environment)).build()


@router.post("/authority/preview", response_model=AuthorityPreviewResponse)
async def preview_authority(payload: AuthorityRequest, request: Request) -> AuthorityPreviewResponse:
    try: scope = AuthorityScope(payload.scope)
    except ValueError as error: raise APIError(status.HTTP_422_UNPROCESSABLE_CONTENT, "INVALID_SCOPE", "The authority scope is invalid.") from error
    application = _application(request)
    try: return AuthorityPreviewResponse(preview=await application.intelligence_service.preview_authority(payload.targets, scope, force=payload.force))
    finally: await application.aclose()


@router.post("/authority/enrich", response_model=list[AuthorityObservation])
async def enrich_authority(payload: AuthorityRequest, request: Request) -> list[AuthorityObservation]:
    try: scope = AuthorityScope(payload.scope)
    except ValueError as error: raise APIError(status.HTTP_422_UNPROCESSABLE_CONTENT, "INVALID_SCOPE", "The authority scope is invalid.") from error
    application = _application(request)
    try:
        if application.authority_provider is None:
            raise APIError(status.HTTP_409_CONFLICT, "PROVIDER_NOT_CONFIGURED", "Moz authority enrichment is not configured.")
        return list(await application.intelligence_service.enrich_authority(payload.targets, scope, force=payload.force))
    finally: await application.aclose()
