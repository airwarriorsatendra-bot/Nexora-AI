"""Typed, evidence-preserving models for bounded technical site crawls."""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from hashlib import sha256
from uuid import UUID, uuid4

from pydantic import ConfigDict, Field, HttpUrl, model_validator

from src.shared.base.base_model import NexoraModel


class IndexabilitySignal(str, Enum):
    INDEXABLE = "INDEXABLE"
    NON_INDEXABLE = "NON_INDEXABLE"
    CANONICALIZED = "CANONICALIZED"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"


class SiteCrawlRequest(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    start_url: HttpUrl
    max_pages: int = Field(default=100, ge=1, le=500)
    max_depth: int = Field(default=4, ge=0, le=10)
    max_concurrency: int = Field(default=4, ge=1, le=10)
    same_host_only: bool = True
    include_subdomains: bool = False
    timeout_seconds: float = Field(default=30.0, gt=0, le=60)
    request_delay_seconds: float = Field(default=0.0, ge=0, le=5)

    @property
    def fingerprint(self) -> str:
        return sha256(self.model_dump_json().encode()).hexdigest()


class InternalLink(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_url: str
    target_url: str
    anchor_text: str = ""
    nofollow: bool = False
    depth: int = Field(ge=0)
    target_status: int | None = None
    issue: str | None = None


class RedirectEdge(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_url: str
    target_url: str
    status_code: int = Field(ge=300, le=399)


class CrawlIssue(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    code: str
    category: str
    severity: str
    affected_url: str
    evidence: str
    recommendation: str


class CrawledPage(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    url: str
    normalized_url: str
    status_code: int | None = None
    content_type: str = ""
    title: str = ""
    meta_description: str = ""
    h1s: tuple[str, ...] = ()
    canonical: str | None = None
    robots: str = ""
    indexability: IndexabilitySignal = IndexabilitySignal.UNKNOWN
    word_count: int = Field(default=0, ge=0)
    internal_links: int = Field(default=0, ge=0)
    external_links: int = Field(default=0, ge=0)
    image_count: int = Field(default=0, ge=0)
    missing_alt_count: int = Field(default=0, ge=0)
    structured_data_types: tuple[str, ...] = ()
    depth: int = Field(ge=0)
    discovered_from: str | None = None
    inlink_count: int = Field(default=0, ge=0)
    outlink_count: int = Field(default=0, ge=0)
    crawled_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    issues: tuple[str, ...] = ()
    error: str | None = None


class LinkOpportunity(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    priority: int = Field(ge=0, le=100)
    target_url: str
    evidence: tuple[str, ...]
    suggested_action: str
    provenance: tuple[str, ...] = ()


class CrawlStatistics(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    pages_crawled: int = 0
    indexable_signals: int = 0
    broken_links: int = 0
    redirects: int = 0
    internal_links: int = 0
    no_crawled_inlinks: int = 0
    depth_four_plus: int = 0
    duplicate_titles: int = 0
    missing_meta: int = 0


class TechnicalSiteSummary(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    overall_score: float = Field(ge=0, le=100)
    category_scores: dict[str, float]
    statistics: CrawlStatistics
    disclaimer: str = "Nexora technical signals are deterministic observations, not a Google ranking or index-status score."


class SiteCrawl(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    crawl_id: UUID = Field(default_factory=uuid4)
    request: SiteCrawlRequest
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    pages: tuple[CrawledPage, ...] = ()
    links: tuple[InternalLink, ...] = ()
    redirects: tuple[RedirectEdge, ...] = ()
    issues: tuple[CrawlIssue, ...] = ()
    opportunities: tuple[LinkOpportunity, ...] = ()
    summary: TechnicalSiteSummary
    robots_txt_supported: bool = False
    sitemap_used: bool = False


class CrawlComparison(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    current_crawl_id: UUID
    previous_crawl_id: UUID | None = None
    new_pages: tuple[str, ...] = ()
    missing_pages: tuple[str, ...] = ()
    new_issues: tuple[str, ...] = ()
    resolved_issues: tuple[str, ...] = ()
    status_changes: tuple[str, ...] = ()
    metadata_changes: tuple[str, ...] = ()
    inlink_changes: tuple[str, ...] = ()
    depth_changes: tuple[str, ...] = ()

