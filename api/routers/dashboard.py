"""Read-only executive dashboard adapter."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.dependencies import DashboardRepositories, dashboard_repositories
from api.schemas.dashboard import ActivityItem, DashboardMetric, DashboardResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "",
    response_model=DashboardResponse,
    summary="Read persisted executive dashboard evidence",
)
async def dashboard(
    repositories: DashboardRepositories = Depends(dashboard_repositories),
) -> DashboardResponse:
    # Repository initialization can issue SQLite DDL on first use. Keep these
    # lightweight persisted reads sequential to avoid competing schema writers.
    prospects = await repositories.prospects.find_all()
    backlinks = await repositories.backlinks.list_backlinks(limit=500, offset=0)
    audits = await repositories.seo.list_recent(limit=500)
    visibility = await repositories.ai_visibility.history(limit=500)
    metrics = [
        DashboardMetric(
            key="tracked_prospects",
            label="Tracked prospects",
            value=len(prospects),
            availability="available",
            description="Persisted prospect records",
            source="RESEARCH",
        ),
        DashboardMetric(
            key="backlink_records",
            label="Backlink records",
            value=len(backlinks),
            availability="available",
            description="Persisted backlink evidence",
            source="BACKLINKS",
        ),
        DashboardMetric(
            key="seo_audits",
            label="SEO audits",
            value=len(audits),
            availability="available",
            description="Current persisted URL audits",
            source="SEO",
        ),
        DashboardMetric(
            key="ai_observations",
            label="AI observations",
            value=len(visibility),
            availability="available",
            description="Persisted visibility observations",
            source="AI_VISIBILITY",
        ),
    ]
    activity: list[ActivityItem] = []
    if audits:
        latest = audits[0]
        activity.append(
            ActivityItem(
                category="SEO",
                title="SEO audit available",
                detail=str(latest.url),
                observed_at=latest.audited_at,
            )
        )
    if visibility:
        latest_observation = visibility[-1]
        activity.append(
            ActivityItem(
                category="AI_VISIBILITY",
                title="AI visibility observation available",
                detail=f"{latest_observation.provider} · {latest_observation.model}",
                observed_at=latest_observation.observed_at,
            )
        )
    activity.sort(
        key=lambda item: item.observed_at.isoformat() if item.observed_at else "",
        reverse=True,
    )
    return DashboardResponse(metrics=metrics, recent_activity=activity[:10], attention_count=0)
