"""Deterministic source-attributed analytics extraction and comparison."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from src.analytics.domain import AnalyticsInsight, AnalyticsReport, ChannelKPI, Period
from src.google_ads.domain import GoogleAdsAudit
from src.meta_ads.domain import MetaAudit


class AnalyticsService:
    """Build reports without combining source-attributed advertising outcomes."""

    def build(
        self,
        period: Period,
        google: GoogleAdsAudit | None = None,
        meta: MetaAudit | None = None,
        *,
        extra_kpis: Iterable[ChannelKPI] = (),
    ) -> AnalyticsReport:
        kpis = list(extra_kpis)
        insights: list[AnalyticsInsight] = []
        audits = (("GOOGLE_ADS", google), ("META_ADS", meta))
        paid_periods: list[tuple[str, Period, str | None]] = []
        for source_module, audit in audits:
            if audit is None:
                continue
            source_period = Period(date_from=audit.period.date_from, date_to=audit.period.date_to)
            currency = audit.account.currency_code if source_module == "GOOGLE_ADS" else audit.account.currency
            spend = sum((campaign.cost if source_module == "GOOGLE_ADS" else campaign.spend for campaign in audit.campaigns), Decimal())
            conversion_value = sum((campaign.conversion_value for campaign in audit.campaigns), Decimal())
            conversions = sum((campaign.conversions for campaign in audit.campaigns), Decimal())
            kpis.extend((
                ChannelKPI(name="spend", value=spend, unit="money", source_module=source_module, source_system=audit.source, period=source_period, source_record_id=str(audit.audit_id), currency=currency),
                ChannelKPI(name="conversion_value", value=conversion_value, unit="money", source_module=source_module, source_system=audit.source, period=source_period, source_record_id=str(audit.audit_id), currency=currency),
                ChannelKPI(name="source_attributed_conversions", value=conversions, unit="count", source_module=source_module, source_system=audit.source, period=source_period, source_record_id=str(audit.audit_id)),
                ChannelKPI(name="roas", value=conversion_value / spend if spend else Decimal(), unit="ratio", source_module=source_module, source_system=audit.source, period=source_period, source_record_id=str(audit.audit_id)),
            ))
            paid_periods.append((source_module, source_period, currency))
            if spend and not conversion_value:
                insights.append(self._insight(
                    "PERFORMANCE", "HIGH", f"{source_module} has spend without conversion value",
                    f"{source_module} source-attributed spend is {spend} {currency} for {source_period.date_from} to {source_period.date_to}.",
                    "Review source-specific conversion measurement before changing campaign spend.", (source_module,), Decimal("0.8"),
                ))
        if len(paid_periods) == 2 and paid_periods[0][1] != paid_periods[1][1]:
            insights.append(self._insight(
                "DATA_QUALITY", "MEDIUM", "Paid-channel reporting periods differ",
                f"Google Ads covers {paid_periods[0][1].date_from} to {paid_periods[0][1].date_to}; Meta Ads covers {paid_periods[1][1].date_from} to {paid_periods[1][1].date_to}.",
                "Compare paid channels only after selecting equivalent reporting periods.", ("GOOGLE_ADS", "META_ADS"), Decimal("1"),
            ))
        if len(paid_periods) == 2 and paid_periods[0][2] != paid_periods[1][2]:
            insights.append(self._insight(
                "DATA_QUALITY", "MEDIUM", "Paid-channel currencies differ",
                f"Google Ads currency is {paid_periods[0][2]}; Meta Ads currency is {paid_periods[1][2]}.",
                "Keep monetary metrics in separate currency groups; no FX conversion is applied.", ("GOOGLE_ADS", "META_ADS"), Decimal("1"),
            ))
        return AnalyticsReport(period=period, kpis=kpis, insights=insights)

    async def build_and_save(self, period: Period, repository: object, google: GoogleAdsAudit | None = None, meta: MetaAudit | None = None, *, extra_kpis: Iterable[ChannelKPI] = ()) -> AnalyticsReport:
        report = self.build(period, google, meta, extra_kpis=extra_kpis)
        await repository.save(report)
        return report

    @staticmethod
    def compare(current: ChannelKPI | None, previous: ChannelKPI | None) -> dict[str, Decimal | int | float | None]:
        """Compare only metrics that are genuinely like-for-like."""
        if (
            current is None or previous is None or current.name != previous.name
            or current.unit != previous.unit or current.currency != previous.currency
            or current.source_module != previous.source_module
            or current.source_system != previous.source_system
            or current.period != previous.period
        ):
            return {"absolute_change": None, "percentage_change": None}
        if not isinstance(current.value, (Decimal, int, float)) or not isinstance(previous.value, (Decimal, int, float)):
            return {"absolute_change": None, "percentage_change": None}
        absolute = current.value - previous.value
        return {"absolute_change": absolute, "percentage_change": None if previous.value == 0 else absolute / previous.value}

    @staticmethod
    def trend(reports: Iterable[AnalyticsReport], name: str, source_module: str) -> list[ChannelKPI]:
        points = [kpi for report in reports for kpi in report.kpis if kpi.name == name and kpi.source_module == source_module]
        if len(points) < 2:
            return []
        semantics = {(point.unit, point.currency, point.source_system) for point in points}
        return points if len(semantics) == 1 else []

    @staticmethod
    def _insight(category: str, priority: str, title: str, evidence: str, recommendation: str, sources: tuple[str, ...], confidence: Decimal) -> AnalyticsInsight:
        return AnalyticsInsight(category=category, priority=priority, title=title, evidence=evidence, recommendation=recommendation, source_modules=sources, confidence=confidence)
