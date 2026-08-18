"""Offline contracts for deterministic, provenance-preserving SEO intelligence."""
from __future__ import annotations
from datetime import date
from decimal import Decimal
import unittest
from src.ga4.domain import GA4Dimension, GA4Property, GA4Record, GA4Snapshot, ReportingPeriod as GA4Period
from src.search_console.domain import ReportingPeriod, SearchConsoleProperty, SearchDimension, SearchPerformanceRecord, SearchPerformanceSnapshot
from src.seo.domain.seo_intelligence import SEOOpportunityType, SEOTrend
from src.seo.services.seo_intelligence_service import SEOIntelligenceService

PROPERTY = SearchConsoleProperty(site_url="https://example.com", permission_level="owner")
CURRENT = ReportingPeriod(start_date=date(2026, 8, 1), end_date=date(2026, 8, 28))
PREVIOUS = ReportingPeriod(start_date=date(2026, 7, 4), end_date=date(2026, 7, 31))

def snapshot(period, dimensions, rows):
    return SearchPerformanceSnapshot(property=PROPERTY, period=period, dimensions=dimensions, records=tuple(rows))

def row(dimensions, key, clicks, impressions, ctr, position):
    return SearchPerformanceRecord(dimensions=dimensions, keys=(key,), clicks=clicks, impressions=impressions, ctr=Decimal(ctr), average_position=Decimal(position))

class SEOIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.service = SEOIntelligenceService()
        self.current_queries = snapshot(CURRENT, (SearchDimension.QUERY,), [row((SearchDimension.QUERY,), "sustainable guide", 12, 1200, ".01", "8"), row((SearchDimension.QUERY,), "new demand", 4, 150, ".026", "12")])
        self.previous_queries = snapshot(PREVIOUS, (SearchDimension.QUERY,), [row((SearchDimension.QUERY,), "sustainable guide", 40, 800, ".05", "5"), row((SearchDimension.QUERY,), "lost query", 10, 120, ".08", "7")])

    def test_query_classification_scoring_and_equal_period_comparison(self):
        report = self.service.analyze(current_queries=self.current_queries, current_pages=None, previous_queries=self.previous_queries)
        types = {item.opportunity_type for item in report.query_opportunities if item.subject == "sustainable guide"}
        self.assertTrue({SEOOpportunityType.STRIKING_DISTANCE, SEOOpportunityType.LOW_CTR, SEOOpportunityType.HIGH_VISIBILITY_LOW_CLICK, SEOOpportunityType.DECLINING}.issubset(types))
        item = next(item for item in report.query_opportunities if item.subject == "sustainable guide" and item.opportunity_type == SEOOpportunityType.LOW_CTR)
        self.assertEqual(item.priority_score, item.score_breakdown.total)
        self.assertLessEqual(item.priority_score, 100)
        self.assertEqual(item.comparison.trend, SEOTrend.DECLINED)
        emerging = [item for item in report.query_opportunities if item.subject == "new demand"]
        self.assertTrue(any(item.opportunity_type == SEOOpportunityType.EMERGING for item in emerging))

    def test_no_data_and_unequal_periods_do_not_infer_trends(self):
        self.assertFalse(self.service.analyze(current_queries=None, current_pages=None).opportunities)
        unequal = snapshot(ReportingPeriod(start_date=date(2026, 7, 5), end_date=date(2026, 7, 31)), (SearchDimension.QUERY,), self.previous_queries.records)
        report = self.service.analyze(current_queries=self.current_queries, current_pages=None, previous_queries=unequal)
        self.assertFalse(any(item.comparison for item in report.query_opportunities))

    def test_page_aggregation_and_url_matched_ga4_evidence_are_conservative(self):
        pages = snapshot(CURRENT, (SearchDimension.PAGE,), [row((SearchDimension.PAGE,), "https://example.com/guide", 30, 1600, ".018", "9")])
        ga4 = GA4Snapshot(property=GA4Property(property_id="1"), period=GA4Period(start_date=CURRENT.start_date, end_date=CURRENT.end_date), dimensions=(GA4Dimension.LANDING_PAGE,), metrics=("engagementRate",), records=(GA4Record(dimensions=(GA4Dimension.LANDING_PAGE,), keys=("/guide",), metrics={"engagementRate": Decimal(".20")}),))
        report = self.service.analyze(current_queries=None, current_pages=pages, ga4_landing_pages=ga4)
        weak = next(item for item in report.page_opportunities if item.opportunity_type == SEOOpportunityType.WEAK_ENGAGEMENT)
        self.assertEqual(weak.ga4_engagement_rate, Decimal(".20"))
        self.assertIn("not attributed", " ".join(weak.evidence))

    def test_zero_division_and_position_direction_are_explicit(self):
        current = snapshot(CURRENT, (SearchDimension.QUERY,), [row((SearchDimension.QUERY,), "query", 2, 20, ".1", "4")])
        previous = snapshot(PREVIOUS, (SearchDimension.QUERY,), [row((SearchDimension.QUERY,), "query", 0, 0, "0", "9")])
        report = self.service.analyze(current_queries=current, current_pages=None, previous_queries=previous)
        emerging = next(item for item in report.query_opportunities if item.opportunity_type == SEOOpportunityType.EMERGING)
        self.assertIsNone(emerging.comparison.click_delta_pct)
        self.assertEqual(emerging.comparison.trend, SEOTrend.NEW)
