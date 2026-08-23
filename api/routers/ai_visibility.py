"""Dedicated adapter for the existing AI Visibility composition."""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from api.errors import APIError
from api.schemas.ai_visibility import (
    AddPromptRequest,
    AIVisibilitySnapshot,
    VisibilityRunPreview,
    VisibilityRunRequest,
    VisibilityRunResponse,
)
from src.ai_visibility.composition import AIVisibilityApplication, AIVisibilityComposition, AIVisibilitySettings
from src.ai_visibility.domain import MonitoredPrompt, VisibilityRequest

router = APIRouter(prefix="/ai-visibility", tags=["ai-visibility"])

def _json_models(values):
    return [value.model_dump(mode="json") if hasattr(value, "model_dump") else value for value in values]


async def visibility_application(request: Request) -> AsyncIterator[AIVisibilityApplication]:
    environment = request.app.state.settings.environment_dict()
    environment["DATABASE_URL"] = str(request.app.state.settings.database_path)
    application = AIVisibilityComposition(AIVisibilitySettings.from_environment(environment)).build()
    try:
        yield application
    finally:
        await application.aclose()


def _preview(payload: VisibilityRunRequest) -> VisibilityRunPreview:
    return VisibilityRunPreview(
        prompts=len(payload.prompt_ids),
        providers=len(payload.provider_names),
        repetitions=payload.repetitions,
        total_api_calls=len(payload.prompt_ids) * len(payload.provider_names) * payload.repetitions,
    )


@router.get("", response_model=AIVisibilitySnapshot)
async def snapshot(application: AIVisibilityApplication = Depends(visibility_application)) -> AIVisibilitySnapshot:
    return AIVisibilitySnapshot(
        providers=[provider.capability for provider in application.providers],
        prompts=await application.prompts(),
        history=await application.history(),
    )


@router.post("/prompts", response_model=MonitoredPrompt, status_code=status.HTTP_201_CREATED)
async def add_prompt(payload: AddPromptRequest, application: AIVisibilityApplication = Depends(visibility_application)) -> MonitoredPrompt:
    return await application.add_prompt(payload.text)


@router.get("/prompts", response_model=list[MonitoredPrompt])
async def prompts(application: AIVisibilityApplication = Depends(visibility_application)) -> list[MonitoredPrompt]:
    return list(await application.prompts())


@router.get("/history", response_model=list[dict])
async def history(application: AIVisibilityApplication = Depends(visibility_application)):
    return _json_models(await application.history())


@router.get("/source-domains", response_model=list[dict])
async def source_domains(
    target_domain: str = Query(default="", max_length=253),
    application: AIVisibilityApplication = Depends(visibility_application),
):
    from src.ai_visibility.citation_intelligence import CitationIntelligenceService
    return _json_models(CitationIntelligenceService().source_domains(await application.history(), target_domain))


@router.get("/stability", response_model=list[dict])
async def stability(application: AIVisibilityApplication = Depends(visibility_application)):
    from src.ai_visibility.citation_intelligence import CitationIntelligenceService
    return _json_models(CitationIntelligenceService().stability(await application.history()))


@router.get("/page-intelligence", response_model=list[dict])
async def page_intelligence(
    target_domain: str = Query(min_length=1, max_length=253),
    application: AIVisibilityApplication = Depends(visibility_application),
):
    return _json_models(await application.page_intelligence(target_domain))


@router.post("/runs/preview", response_model=VisibilityRunPreview)
async def preview(payload: VisibilityRunRequest) -> VisibilityRunPreview:
    return _preview(payload)


@router.post("/runs", response_model=VisibilityRunResponse)
async def run(payload: VisibilityRunRequest, application: AIVisibilityApplication = Depends(visibility_application)) -> VisibilityRunResponse:
    configured = {provider.capability.provider for provider in application.providers}
    if not configured:
        raise APIError(status.HTTP_409_CONFLICT, "PROVIDER_NOT_CONFIGURED", "No AI visibility provider is configured.")
    if not set(payload.provider_names).issubset(configured):
        raise APIError(status.HTTP_422_UNPROCESSABLE_CONTENT, "INVALID_PROVIDER", "A selected provider is not configured.")
    prompts = {str(prompt.prompt_id): prompt for prompt in await application.prompts()}
    try:
        selected = [prompts[str(UUID(prompt_id))] for prompt_id in payload.prompt_ids]
    except (ValueError, KeyError) as error:
        raise APIError(status.HTTP_404_NOT_FOUND, "PROMPT_NOT_FOUND", "A selected monitoring prompt was not found.") from error
    requests = [
        VisibilityRequest(
            prompt=prompt,
            brand_name=payload.brand_name,
            brand_aliases=tuple(payload.brand_aliases),
            target_domain=payload.target_domain,
            competitors={name: tuple(aliases) for name, aliases in payload.competitors.items()},
        )
        for prompt in selected
    ]
    report = await application.run(requests, payload.repetitions, payload.provider_names)
    return VisibilityRunResponse(preview=_preview(payload), report=report)
