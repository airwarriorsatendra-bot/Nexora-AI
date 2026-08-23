"""Small read adapters for persisted vertical summaries."""

from __future__ import annotations

from fastapi import APIRouter, Request

from api.config import APISettings
from api.schemas.dashboard import DashboardMetric
from api.schemas.workspace import WorkspaceSummary
from src.ai_visibility.repository import AIVisibilityRepository
from src.analytics.repository import AnalyticsRepository
from src.google_ads.repository import GoogleAdsRepository
from src.local_seo.repository import LocalSEORepository
from src.meta_ads.repository import MetaAdsRepository
from src.outreach.repositories.outreach_repository import OutreachAutomationRepository

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _metric(key: str, label: str, value: int, source: str, description: str) -> DashboardMetric:
    return DashboardMetric(key=key, label=label, value=value, availability="available", description=description, source=source)


@router.get("/ai-visibility", response_model=WorkspaceSummary)
async def ai_visibility(request: Request) -> WorkspaceSummary:
    path = request.app.state.settings.database_path
    repository = AIVisibilityRepository(path)
    prompt_count = await repository.count_prompts()
    observations = await repository.history(limit=500)
    return WorkspaceSummary(workspace="AI Visibility", metrics=[_metric("prompts", "Monitored prompts", prompt_count, "AI_VISIBILITY", "Persisted prompt records"), _metric("observations", "Observations", await repository.count_observations(), "AI_VISIBILITY", "Persisted provider evidence")], note="Provider execution remains an explicit action.")


@router.get("/outreach", response_model=WorkspaceSummary)
async def outreach(request: Request) -> WorkspaceSummary:
    repository = OutreachAutomationRepository(request.app.state.settings.database_path)
    counts = await repository.summary_counts()
    metrics = [_metric(key, key.replace("_", " ").title(), value, "OUTREACH", "Persisted CRM records") for key, value in counts.items()]
    return WorkspaceSummary(workspace="Outreach", metrics=metrics, note="Gmail sending and reply checks are never triggered by this read endpoint.")


@router.get("/local-seo", response_model=WorkspaceSummary)
async def local_seo(request: Request) -> WorkspaceSummary:
    repository = LocalSEORepository(request.app.state.settings.database_path)
    return WorkspaceSummary(workspace="Local SEO", metrics=[_metric("locations", "Locations", await repository.count_locations(), "LOCAL_SEO", "Persisted business locations"), _metric("reviews", "Reviews", await repository.count_reviews(), "LOCAL_SEO", "Persisted review evidence"), _metric("opportunities", "Opportunities", await repository.count_opportunities(), "LOCAL_SEO", "Deterministic local actions")], note="Google Business Profile refresh remains explicit.")


@router.get("/analytics", response_model=WorkspaceSummary)
async def analytics(request: Request) -> WorkspaceSummary:
    repository = AnalyticsRepository(request.app.state.settings.database_path)
    history = await repository.history(limit=100)
    latest = history[0] if history else None
    return WorkspaceSummary(workspace="Analytics", metrics=[_metric("reports", "Recent reports", len(history), "ANALYTICS", "Recent persisted source-attributed reports (up to 100)"), _metric("kpis", "Latest KPIs", len(latest.kpis) if latest else 0, "ANALYTICS", "Source-specific metrics"), _metric("insights", "Insights", len(latest.insights) if latest else 0, "ANALYTICS", "Deterministic recommendations")], note="GSC clicks and GA4 sessions retain separate source semantics.")


@router.get("/google-ads", response_model=WorkspaceSummary)
async def google_ads(request: Request) -> WorkspaceSummary:
    audits = await GoogleAdsRepository(request.app.state.settings.database_path).list_recent(100)
    latest = audits[0] if audits else None
    return WorkspaceSummary(workspace="Google Ads", metrics=[_metric("imports", "Imported audits", len(audits), "GOOGLE_ADS", "Offline imported snapshots"), _metric("campaigns", "Campaigns", len(latest.campaigns) if latest else 0, "GOOGLE_ADS", "Latest imported snapshot"), _metric("recommendations", "Recommendations", len(latest.recommendations) if latest else 0, "GOOGLE_ADS", "Existing deterministic findings")], note="Beta 17 preserves the current import-only scope.")


@router.get("/meta-ads", response_model=WorkspaceSummary)
async def meta_ads(request: Request) -> WorkspaceSummary:
    audits = await MetaAdsRepository(request.app.state.settings.database_path).list_recent()
    latest = audits[0] if audits else None
    return WorkspaceSummary(workspace="Meta Ads", metrics=[_metric("imports", "Imported audits", len(audits), "META_ADS", "Offline imported snapshots"), _metric("campaigns", "Campaigns", len(latest.campaigns) if latest else 0, "META_ADS", "Latest imported snapshot"), _metric("recommendations", "Recommendations", len(latest.recommendations) if latest else 0, "META_ADS", "Existing deterministic findings")], note="Beta 17 preserves the current import-only scope.")
