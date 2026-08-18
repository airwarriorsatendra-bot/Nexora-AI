"""Immutable, evidence-preserving AEO/GEO readiness models."""
from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import ConfigDict, Field

from src.shared.base.base_model import NexoraModel


class ReadinessLevel(str, Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class QuestionType(str, Enum):
    WHO = "WHO"; WHAT = "WHAT"; WHEN = "WHEN"; WHERE = "WHERE"; WHY = "WHY"
    HOW = "HOW"; WHICH = "WHICH"; CAN = "CAN"; DOES = "DOES"; IS = "IS"
    ARE = "ARE"; SHOULD = "SHOULD"; BEST_WAY = "BEST_WAY"
    DIFFERENCE_BETWEEN = "DIFFERENCE_BETWEEN"; VS = "VS"; MEANING_OF = "MEANING_OF"; OTHER = "OTHER"


class FAQStatus(str, Enum):
    FAQ_ALREADY_SUPPORTED = "FAQ_ALREADY_SUPPORTED"
    FAQ_CONTENT_OPPORTUNITY = "FAQ_CONTENT_OPPORTUNITY"
    FAQ_SCHEMA_OBSERVED = "FAQ_SCHEMA_OBSERVED"
    FAQ_SCHEMA_NOT_OBSERVED = "FAQ_SCHEMA_NOT_OBSERVED"


class QuestionOpportunity(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    query: str
    question_type: QuestionType
    mapped_page: str | None = None
    clicks: int | None = None
    impressions: int | None = None
    ctr: Decimal | None = None
    gsc_average_position: Decimal | None = None
    tracked_serp_position: int | None = None
    confidence: Decimal = Field(ge=0, le=1)
    priority_score: int = Field(ge=0, le=100)
    evidence: tuple[str, ...] = ()
    recommended_action: str


class AEOScoreBreakdown(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    question_coverage: int = 0
    direct_answer_structure: int = 0
    faq_schema: int = 0
    heading_structure: int = 0
    content_clarity: int = 0
    technical_accessibility: int = 0
    total: int = Field(ge=0, le=100)


class GEOScoreBreakdown(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    extractability: int = 0
    entity_clarity: int = 0
    source_support: int = 0
    structured_data: int = 0
    topic_clarity: int = 0
    technical_accessibility: int = 0
    total: int = Field(ge=0, le=100)


class PageReadiness(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    url: str
    aeo: AEOScoreBreakdown
    geo: GEOScoreBreakdown
    aeo_level: ReadinessLevel
    geo_level: ReadinessLevel
    faq_status: FAQStatus
    question_opportunities: int = 0
    structured_data_types: tuple[str, ...] = ()
    observations: tuple[str, ...] = ()
    technical_issues: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()


class AEOGEOReport(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    target_domain: str
    questions: tuple[QuestionOpportunity, ...] = ()
    pages: tuple[PageReadiness, ...] = ()
    notes: tuple[str, ...] = ()
