"""Offline hardening tests for Analytics persistence and data honesty."""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from dashboard.analytics_workflow import insights_to_dataframe, kpis_to_dataframe
from src.analytics.composition import AnalyticsComposition, AnalyticsSettings
from src.analytics.domain import ChannelKPI, Period
from src.analytics.repository import AnalyticsRepository
from src.analytics.service import AnalyticsService
from src.google_ads.domain import GoogleAdsAccount, GoogleAdsAudit, GoogleAdsCampaign, ReportingPeriod
from src.meta_ads.domain import MetaAccount, MetaAudit, MetaCampaign, Period as MetaPeriod


def google(period: Period, currency: str = "INR", cost: Decimal = Decimal("100")) -> GoogleAdsAudit:
    return GoogleAdsAudit(
        account=GoogleAdsAccount(customer_id="1", currency_code=currency),
        period=ReportingPeriod(date_from=period.date_from, date_to=period.date_to), source="TEST_FIXTURE",
        campaigns=[GoogleAdsCampaign(campaign_id="g", name="Google", impressions=100, clicks=10, cost=cost, conversions=Decimal("5"), conversion_value=Decimal("500"))],
    )


def meta(period: Period, currency: str = "INR") -> MetaAudit:
    return MetaAudit(
        account=MetaAccount(ad_account_id="2", currency=currency), period=MetaPeriod(date_from=period.date_from, date_to=period.date_to), source="TEST_FIXTURE",
        campaigns=[MetaCampaign(campaign_id="m", name="Meta", impressions=100, reach=80, clicks=8, spend=Decimal("80"), conversions=Decimal("4"), conversion_value=Decimal("240"))],
    )


class AnalyticsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.repository = AnalyticsRepository(Path(self.directory.name) / "analytics.db")
        self.service = AnalyticsService()
        self.period = Period(date_from=date(2026, 8, 1), date_to=date(2026, 8, 15))

    async def asyncTearDown(self) -> None:
        self.directory.cleanup()

    async def test_domain_validation_and_decimal_money(self) -> None:
        with self.assertRaises(ValueError):
            Period(date_from=self.period.date_to, date_to=self.period.date_from - timedelta(days=1))
        with self.assertRaises(ValueError):
            ChannelKPI(name="spend", value=1.5, unit="money", source_module="TEST", source_system="TEST", period=self.period, currency="INR")
        with self.assertRaises(ValueError):
            ChannelKPI(name="spend", value=Decimal("1"), unit="money", source_module="TEST", source_system="TEST", period=self.period)

    async def test_provenance_attribution_and_mixed_currency_are_explicit(self) -> None:
        later = Period(date_from=date(2026, 8, 1), date_to=date(2026, 8, 31))
        report = self.service.build(self.period, google(self.period, "INR"), meta(later, "USD"))
        self.assertEqual({item.source_module for item in report.kpis}, {"GOOGLE_ADS", "META_ADS"})
        self.assertEqual({item.currency for item in report.kpis if item.name == "spend"}, {"INR", "USD"})
        self.assertEqual(len([item for item in report.kpis if item.name == "source_attributed_conversions"]), 2)
        self.assertNotIn("unique", " ".join(item.name for item in report.kpis).lower())
        self.assertTrue({"Paid-channel reporting periods differ", "Paid-channel currencies differ"}.issubset({item.title for item in report.insights}))

    async def test_snapshot_identity_decimal_round_trip_and_concurrent_idempotency(self) -> None:
        audit = google(self.period, cost=Decimal("100.123456789"))
        report = self.service.build(self.period, audit)
        timestamp_variant = report.model_copy(update={"captured_at": datetime.now(UTC) + timedelta(days=1)})
        self.assertEqual(self.repository.snapshot_key(report), self.repository.snapshot_key(timestamp_variant))
        await asyncio.gather(*(self.repository.save(report) for _ in range(8)))
        history = await self.repository.history(source_module="GOOGLE_ADS")
        self.assertEqual(len(history), 1)
        spend = next(item for item in history[0].kpis if item.name == "spend")
        self.assertEqual(spend.value, Decimal("100.123456789"))
        changed = self.service.build(self.period, google(self.period, cost=Decimal("101")))
        self.assertNotEqual(self.repository.snapshot_key(report), self.repository.snapshot_key(changed))
        await self.repository.save(changed)
        self.assertEqual(len(await self.repository.history()), 2)

    async def test_history_comparison_trend_and_filters(self) -> None:
        first = self.service.build(self.period, google(self.period, cost=Decimal("100")))
        second = self.service.build(self.period, google(self.period, cost=Decimal("200")))
        await self.repository.save(first)
        await self.repository.save(second)
        history = await self.repository.history(date_from="2026-08-01", date_to="2026-08-15")
        self.assertEqual(len(history), 2)
        self.assertEqual(await self.repository.history(source_module="META_ADS"), [])
        self.assertEqual((await self.repository.latest()).kpis[0].value, Decimal("200"))
        points = self.service.trend(history, "spend", "GOOGLE_ADS")
        self.assertEqual(len(points), 2)
        self.assertEqual(self.service.compare(points[1], points[0]), {"absolute_change": Decimal("100"), "percentage_change": Decimal("1")})
        self.assertEqual(self.service.compare(points[1], points[0].model_copy(update={"currency": "USD"})), {"absolute_change": None, "percentage_change": None})
        self.assertIsNone(self.service.compare(points[1], points[0].model_copy(update={"value": Decimal("0")}))["percentage_change"])

    async def test_exports_and_composition_lifecycle(self) -> None:
        report = self.service.build(self.period, google(self.period), meta(self.period))
        kpis = kpis_to_dataframe(report, ("GOOGLE_ADS",))
        insights = insights_to_dataframe(report)
        self.assertIn("source_module", kpis.columns)
        self.assertIn("period", kpis.columns)
        self.assertIn("currency", kpis.columns)
        self.assertIn("source_module", kpis.to_csv(index=False))
        self.assertTrue(insights.empty)
        self.assertEqual(kpis_to_dataframe(report, ("SEO",)).to_csv(index=False).strip(), "")
        application = AnalyticsComposition(AnalyticsSettings(Path(self.directory.name) / "composition.db")).build()
        await application.aclose()
        await application.aclose()
        self.assertTrue(application._closed)
