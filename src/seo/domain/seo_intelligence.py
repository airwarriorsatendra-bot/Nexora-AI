"""Immutable, provenance-preserving SEO intelligence models."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import ConfigDict, Field

from src.shared.base.base_model import NexoraModel


class SEOOpportunityType(str, Enum):
    STRIKING_DISTANCE = "STRIKING_DISTANCE"
    LOW_CTR = "LOW_CTR"
    HIGH_VISIBILITY_LOW_CLICK = "HIGH_VISIBILITY_LOW_CLICK"
    WINNER = "WINNER"
    DECLINING = "DECLINING"
    EMERGING = "EMERGING"
    TOP_PERFORMER = "TOP_PERFORMER"
    WEAK_ENGAGEMENT = "WEAK_ENGAGEMENT"


class SEOTrend(str, Enum):
    NEW = "NEW"
    LOST = "LOST"
    IMPROVED = "IMPROVED"
    DECLINED = "DECLINED"
    STABLE = "STABLE"


class SEOScoreBreakdown(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    impressions: int = Field(ge=0, le=35)
    position: int = Field(ge=0, le=25)
    ctr: int = Field(ge=0, le=25)
    trend: int = Field(ge=0, le=10)
    engagement: int = Field(ge=0, le=5)

    @property
    def total(self) -> int:
        return self.impressions + self.position + self.ctr + self.trend + self.engagement


class SEOComparison(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    trend: SEOTrend
    click_delta: int | None = None
    click_delta_pct: Decimal | None = None
    impression_delta: int | None = None
    impression_delta_pct: Decimal | None = None
    ctr_delta: Decimal | None = None
    position_delta: Decimal | None = None


class SEOOpportunity(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    opportunity_type: SEOOpportunityType
    subject: str = Field(min_length=1)
    subject_kind: str = Field(pattern="^(query|page)$")
    clicks: int = Field(ge=0)
    impressions: int = Field(ge=0)
    ctr: Decimal = Field(ge=0, le=1)
    average_position: Decimal = Field(ge=0)
    priority_score: int = Field(ge=0, le=100)
    score_breakdown: SEOScoreBreakdown
    evidence: tuple[str, ...]
    recommendation: str
    comparison: SEOComparison | None = None
    ga4_engagement_rate: Decimal | None = Field(default=None, ge=0, le=1)
    source: str = "GOOGLE_SEARCH_CONSOLE"


class SEOIntelligenceReport(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    query_opportunities: tuple[SEOOpportunity, ...] = ()
    page_opportunities: tuple[SEOOpportunity, ...] = ()
    gsc_ga4_insights: tuple[SEOOpportunity, ...] = ()
    notes: tuple[str, ...] = ()

    @property
    def opportunities(self) -> tuple[SEOOpportunity, ...]:
        return self.query_opportunities + self.page_opportunities + self.gsc_ga4_insights
