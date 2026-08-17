"""Dashboard adapter for persisted, source-attributed Analytics reports."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

import pandas as pd

from src.analytics.composition import AnalyticsApplication, AnalyticsComposition, AnalyticsSettings
from src.analytics.domain import AnalyticsReport, ChannelKPI, Period


class AnalyticsDashboardWorkflow:
    """Reads the existing source repositories and owns composition cleanup."""

    def __init__(self, factory: Callable[[], AnalyticsApplication] | None = None) -> None:
        self._factory = factory or (lambda: AnalyticsComposition(AnalyticsSettings.from_environment()).build())

    async def latest_report(self) -> AnalyticsReport | None:
        application = self._factory()
        try:
            google = await application.google_repository.list_recent(1)
            meta = await application.meta_repository.list_recent()
            seo = await application.seo_repository.list_recent(1)
            local_seo = await application.local_seo_repository.list_recent(1)
            backlinks = await application.backlink_repository.list_backlinks(limit=500)
            opportunities = await application.backlink_repository.list_opportunities(limit=500)
            outreach = await application.outreach_repository.summary_counts()
            latest_google = google[0] if google else None
            latest_meta = meta[0] if meta else None
            if latest_google is None and latest_meta is None and not seo and not local_seo and not backlinks and not opportunities and not any(outreach.values()):
                return None
            reference = latest_google.period if latest_google is not None else latest_meta.period if latest_meta is not None else None
            if reference is None:
                observed_at = seo[0].audited_at.date() if seo else local_seo[0].audited_at.date() if local_seo else date.today()
                period = Period(date_from=observed_at, date_to=observed_at)
            else:
                period = Period(date_from=reference.date_from, date_to=reference.date_to)
            extra_kpis: list[ChannelKPI] = []
            if seo:
                audit = seo[0]
                observed = Period(date_from=audit.audited_at.date(), date_to=audit.audited_at.date())
                extra_kpis.extend((ChannelKPI(name="audit_score", value=audit.overall_score, unit="score", source_module="SEO", source_system="AUDIT", period=observed, source_record_id=str(audit.audit_id)), ChannelKPI(name="issue_count", value=audit.issue_count, unit="count", source_module="SEO", source_system="AUDIT", period=observed, source_record_id=str(audit.audit_id))))
            if local_seo:
                audit = local_seo[0]
                observed = Period(date_from=audit.audited_at.date(), date_to=audit.audited_at.date())
                extra_kpis.extend((ChannelKPI(name="audit_score", value=audit.overall_score, unit="score", source_module="LOCAL_SEO", source_system="AUDIT", period=observed, source_record_id=str(audit.audit_id)), ChannelKPI(name="issue_count", value=len(audit.issues), unit="count", source_module="LOCAL_SEO", source_system="AUDIT", period=observed, source_record_id=str(audit.audit_id))))
            if backlinks or opportunities:
                extra_kpis.extend((ChannelKPI(name="verified_backlinks", value=sum(link.is_verified for link in backlinks), unit="count", source_module="BACKLINKS", source_system="REPOSITORY", period=period), ChannelKPI(name="backlink_opportunities", value=len(opportunities), unit="count", source_module="BACKLINKS", source_system="REPOSITORY", period=period)))
            if any(outreach.values()):
                extra_kpis.extend(ChannelKPI(name=name, value=value, unit="count", source_module="OUTREACH", source_system="REPOSITORY", period=period) for name, value in outreach.items())
            return await application.service.build_and_save(
                period,
                application.repository,
                latest_google,
                latest_meta,
                extra_kpis=extra_kpis,
            )
        finally:
            await application.aclose()

    async def history(self, source_module: str | None = None) -> list[AnalyticsReport]:
        application = self._factory()
        try:
            return await application.repository.history(source_module=source_module)
        finally:
            await application.aclose()


def kpis_to_dataframe(report: AnalyticsReport, sources: tuple[str, ...] = ()) -> pd.DataFrame:
    rows = [kpi.model_dump(mode="json") for kpi in report.kpis if not sources or kpi.source_module in sources]
    return pd.DataFrame(rows)


def insights_to_dataframe(report: AnalyticsReport) -> pd.DataFrame:
    return pd.DataFrame([insight.model_dump(mode="json") for insight in report.insights])
