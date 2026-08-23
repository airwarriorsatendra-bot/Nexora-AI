"""Read-only, presence-only configuration status."""

from __future__ import annotations

from fastapi import APIRouter, Request

from api.schemas.settings import ProviderStatus, ProviderStatusResponse

router = APIRouter(prefix="/settings", tags=["settings"])


def _configured(environment: dict[str, str], *names: str) -> bool:
    return all(bool(environment.get(name, "").strip()) for name in names)


@router.get("/providers", response_model=ProviderStatusResponse)
async def provider_status(request: Request) -> ProviderStatusResponse:
    environment = request.app.state.settings.environment_dict()
    definitions = (
        ("Google Search Console", ("GSC_CLIENT_ID", "GSC_CLIENT_SECRET", "GSC_REFRESH_TOKEN"), "Read-only OAuth"),
        ("Google Analytics 4", ("GSC_CLIENT_ID", "GSC_CLIENT_SECRET", "GSC_REFRESH_TOKEN", "GA4_PROPERTY_ID"), "Shared read-only OAuth"),
        ("Moz", ("MOZ_API_TOKEN",), "Explicit authority enrichment"),
        ("Gmail", ("GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN", "GMAIL_SENDER_EMAIL"), "Explicit safeguarded delivery"),
        ("Google Business Profile", ("GBP_CLIENT_ID", "GBP_CLIENT_SECRET", "GBP_REFRESH_TOKEN"), "Explicit profile refresh"),
        ("SERP", ("SERPER_API_KEY",), "Explicit rank checks"),
        ("AI generation", ("AI_PROVIDER",), "Replaceable backend provider"),
    )
    providers = [
        ProviderStatus(
            provider=label,
            status="CONFIGURED" if _configured(environment, *variables) else "MISSING",
            detail=detail,
        )
        for label, variables, detail in definitions
    ]
    providers.append(ProviderStatus(provider="Offline repositories", status="OFFLINE_READY", detail="SQLite persisted evidence"))
    return ProviderStatusResponse(providers=providers)
