"""Deterministic SEO opportunity analysis over persisted source snapshots."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from urllib.parse import urlsplit

from src.ga4.domain import GA4Dimension, GA4Snapshot
from src.search_console.domain import SearchDimension, SearchPerformanceRecord, SearchPerformanceSnapshot
from src.seo.domain.seo_intelligence import SEOComparison, SEOIntelligenceReport, SEOOpportunity, SEOOpportunityType, SEOScoreBreakdown, SEOTrend


class SEOIntelligenceService:
    """Scores available GSC evidence locally; it never fetches external data."""

    minimum_impressions = 100
    low_ctr_heuristic = Decimal("0.03")

    def analyze(
        self,
        *,
        current_queries: SearchPerformanceSnapshot | None,
        current_pages: SearchPerformanceSnapshot | None,
        previous_queries: SearchPerformanceSnapshot | None = None,
        previous_pages: SearchPerformanceSnapshot | None = None,
        ga4_landing_pages: GA4Snapshot | None = None,
    ) -> SEOIntelligenceReport:
        notes: list[str] = []
        query_opportunities = self._opportunities(current_queries, previous_queries, "query", None)
        page_engagement = self._engagement_by_path(ga4_landing_pages, current_pages)
        page_opportunities = self._opportunities(current_pages, previous_pages, "page", page_engagement)
        gsc_ga4 = tuple(item for item in page_opportunities if item.opportunity_type == SEOOpportunityType.WEAK_ENGAGEMENT)
        if current_queries is None and current_pages is None:
            notes.append("No persisted Google Search Console snapshots are available. Refresh Search Performance explicitly first.")
        elif previous_queries is None and previous_pages is None:
            notes.append("No equal-length preceding snapshot is available; trend labels are omitted rather than inferred.")
        if ga4_landing_pages is None:
            notes.append("GA4 landing-page evidence is not available for the selected GSC period.")
        return SEOIntelligenceReport(query_opportunities=query_opportunities, page_opportunities=page_opportunities, gsc_ga4_insights=gsc_ga4, notes=tuple(notes))

    def _opportunities(self, current: SearchPerformanceSnapshot | None, previous: SearchPerformanceSnapshot | None, kind: str, engagement: dict[str, Decimal] | None) -> tuple[SEOOpportunity, ...]:
        if current is None:
            return ()
        previous_rows = {self._key(row): row for row in previous.records} if self._comparable(current, previous) else {}
        has_comparable_previous = bool(previous_rows)
        items: list[SEOOpportunity] = []
        for record in current.records:
            subject = self._key(record)
            if not subject:
                continue
            comparison = self._comparison(record, previous_rows.get(subject), has_comparable_previous)
            matched_engagement = (engagement or {}).get(self._path(subject)) if kind == "page" else None
            for opportunity_type in self._classifications(record, comparison, matched_engagement):
                items.append(self._build(opportunity_type, subject, kind, record, comparison, matched_engagement))
        return tuple(sorted(items, key=lambda item: (-item.priority_score, -item.impressions, item.subject, item.opportunity_type.value)))

    def _classifications(self, record: SearchPerformanceRecord, comparison: SEOComparison | None, engagement: Decimal | None) -> tuple[SEOOpportunityType, ...]:
        types: list[SEOOpportunityType] = []
        if record.impressions >= self.minimum_impressions and Decimal("3") < record.average_position <= Decimal("15"):
            types.append(SEOOpportunityType.STRIKING_DISTANCE)
        if record.impressions >= self.minimum_impressions and record.ctr < self.low_ctr_heuristic:
            types.append(SEOOpportunityType.LOW_CTR)
        if record.impressions >= self.minimum_impressions and record.clicks <= max(1, record.impressions // 100):
            types.append(SEOOpportunityType.HIGH_VISIBILITY_LOW_CLICK)
        if comparison:
            if comparison.trend == SEOTrend.IMPROVED:
                types.append(SEOOpportunityType.WINNER)
            elif comparison.trend == SEOTrend.DECLINED:
                types.append(SEOOpportunityType.DECLINING)
            elif comparison.trend == SEOTrend.NEW:
                types.append(SEOOpportunityType.EMERGING)
        if record.clicks > 0 and record.impressions > 0 and record.average_position <= Decimal("3"):
            types.append(SEOOpportunityType.TOP_PERFORMER)
        if engagement is not None and engagement < Decimal("0.30") and record.impressions >= self.minimum_impressions:
            types.append(SEOOpportunityType.WEAK_ENGAGEMENT)
        return tuple(types)

    def _build(self, kind: SEOOpportunityType, subject: str, subject_kind: str, record: SearchPerformanceRecord, comparison: SEOComparison | None, engagement: Decimal | None) -> SEOOpportunity:
        score = self._score(record, kind, comparison, engagement)
        evidence = [f"{record.clicks} GSC clicks from {record.impressions} impressions", f"GSC average position {record.average_position:g}", f"GSC CTR {record.ctr:.2%}"]
        if comparison is not None:
            evidence.append(f"Trend: {comparison.trend.value} across equal-length persisted periods")
        if engagement is not None:
            evidence.append(f"GA4 landing-page engagement rate {engagement:.2%}; it is not attributed to GSC clicks")
        recommendations = {
            SEOOpportunityType.STRIKING_DISTANCE: "Consider expanding relevant content, strengthening internal links, and reviewing search intent.",
            SEOOpportunityType.LOW_CTR: "Candidate for title/meta and SERP-intent review; the threshold is a Nexora heuristic, not a Google benchmark.",
            SEOOpportunityType.HIGH_VISIBILITY_LOW_CLICK: "Inspect query-to-page relevance and the visible search snippet.",
            SEOOpportunityType.WINNER: "Monitor the demonstrated improvement and preserve relevant content quality.",
            SEOOpportunityType.DECLINING: "Review recent content, indexing, and competitive context; this is a trend, not causal attribution.",
            SEOOpportunityType.EMERGING: "Consider expanding content around demonstrated search demand.",
            SEOOpportunityType.TOP_PERFORMER: "Preserve the page and monitor organic performance without assuming ranking permanence.",
            SEOOpportunityType.WEAK_ENGAGEMENT: "Review landing-page intent alignment and on-page experience; GSC clicks are not GA4 sessions.",
        }
        return SEOOpportunity(opportunity_type=kind, subject=subject, subject_kind=subject_kind, clicks=record.clicks, impressions=record.impressions, ctr=record.ctr, average_position=record.average_position, priority_score=score.total, score_breakdown=score, evidence=tuple(evidence), recommendation=recommendations[kind], comparison=comparison, ga4_engagement_rate=engagement)

    def _score(self, record: SearchPerformanceRecord, kind: SEOOpportunityType, comparison: SEOComparison | None, engagement: Decimal | None) -> SEOScoreBreakdown:
        impressions = min(35, int(record.impressions / 100))
        position = 25 if kind == SEOOpportunityType.STRIKING_DISTANCE else 10 if record.average_position <= Decimal("20") else 0
        ctr = 25 if kind in (SEOOpportunityType.LOW_CTR, SEOOpportunityType.HIGH_VISIBILITY_LOW_CLICK) else 0
        trend = 10 if comparison and comparison.trend in (SEOTrend.DECLINED, SEOTrend.NEW) else 5 if comparison and comparison.trend == SEOTrend.IMPROVED else 0
        engagement_score = 5 if engagement is not None and engagement < Decimal("0.30") else 0
        return SEOScoreBreakdown(impressions=impressions, position=position, ctr=ctr, trend=trend, engagement=engagement_score)

    @staticmethod
    def _key(record: SearchPerformanceRecord) -> str:
        return record.keys[0] if record.keys else ""

    @staticmethod
    def _path(value: str) -> str:
        return urlsplit(value).path.rstrip("/") or "/"

    @staticmethod
    def _comparable(current: SearchPerformanceSnapshot, previous: SearchPerformanceSnapshot | None) -> bool:
        return previous is not None and current.property.site_url == previous.property.site_url and current.dimensions == previous.dimensions and current.period.days == previous.period.days

    def _comparison(self, current: SearchPerformanceRecord, previous: SearchPerformanceRecord | None, has_previous: bool) -> SEOComparison | None:
        if previous is None:
            return SEOComparison(trend=SEOTrend.NEW) if has_previous and (current.impressions or current.clicks) else None
        click_delta, impression_delta = current.clicks - previous.clicks, current.impressions - previous.impressions
        position_delta = current.average_position - previous.average_position
        if previous.impressions == 0 and current.impressions > 0:
            trend = SEOTrend.NEW
        elif current.impressions == 0 and previous.impressions > 0:
            trend = SEOTrend.LOST
        elif click_delta > 0 and position_delta <= 0:
            trend = SEOTrend.IMPROVED
        elif click_delta < 0 and position_delta >= 0:
            trend = SEOTrend.DECLINED
        elif impression_delta > 0 or position_delta < 0:
            trend = SEOTrend.IMPROVED
        elif impression_delta < 0 or position_delta > 0:
            trend = SEOTrend.DECLINED
        else:
            trend = SEOTrend.STABLE
        return SEOComparison(trend=trend, click_delta=click_delta, click_delta_pct=None if previous.clicks == 0 else Decimal(click_delta) / Decimal(previous.clicks), impression_delta=impression_delta, impression_delta_pct=None if previous.impressions == 0 else Decimal(impression_delta) / Decimal(previous.impressions), ctr_delta=current.ctr - previous.ctr, position_delta=position_delta)

    def _engagement_by_path(self, snapshot: GA4Snapshot | None, gsc: SearchPerformanceSnapshot | None) -> dict[str, Decimal]:
        if snapshot is None or gsc is None or snapshot.dimensions != (GA4Dimension.LANDING_PAGE,) or snapshot.period.start_date != gsc.period.start_date or snapshot.period.end_date != gsc.period.end_date:
            return {}
        return {self._path(row.keys[0]): row.metrics["engagementRate"] for row in snapshot.records if row.keys and "engagementRate" in row.metrics}
