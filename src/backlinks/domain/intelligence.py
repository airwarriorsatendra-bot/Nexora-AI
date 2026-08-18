"""Provider-scoped Backlink Intelligence 2.0 domain records."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import ConfigDict, Field, HttpUrl, model_validator

from src.backlinks.domain.normalization import canonical_url, normalized_domain
from src.shared.base.base_model import NexoraModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class AuthorityScope(str, Enum):
    DOMAIN = "domain"
    SUBDOMAIN = "subdomain"
    SUBFOLDER = "subfolder"
    URL = "url"


class AuthorityStatus(str, Enum):
    AVAILABLE = "available"
    NOT_AVAILABLE = "not_available"
    NOT_REQUESTED = "not_requested"
    PROVIDER_ERROR = "provider_error"


class AuthorityHistoryState(str, Enum):
    NEW = "new"
    INCREASED = "increased"
    DECREASED = "decreased"
    STABLE = "stable"
    UNAVAILABLE = "unavailable"


class ObservedGapState(str, Enum):
    OBSERVED_COMPETITOR_LINK = "observed_competitor_link"
    OBSERVED_TARGET_LINK = "observed_target_link"
    COMPETITOR_ONLY_OBSERVED = "competitor_only_observed"
    TARGET_ONLY_OBSERVED = "target_only_observed"
    SHARED_OBSERVED = "shared_observed"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ObservedLinkState(str, Enum):
    NEWLY_OBSERVED = "newly_observed"
    STILL_OBSERVED = "still_observed"
    LOST_FROM_PROVIDER_DATASET = "lost_from_provider_dataset"
    REAPPEARED = "reappeared"
    UNKNOWN = "unknown"


class ProspectOpportunityType(str, Enum):
    COMPETITOR_LINK_GAP = "competitor_link_gap"
    LINK_INTERSECT = "link_intersect"
    RESOURCE_PAGE = "resource_page"
    LISTICLE = "listicle"
    GUEST_POST = "guest_post"
    EDITORIAL_MENTION = "editorial_mention"
    BROKEN_LINK = "broken_link"
    UNLINKED_BRAND = "unlinked_brand"
    CONTENT_REFERENCE = "content_reference"
    LINK_RECLAMATION = "link_reclamation"
    OTHER_RELEVANT_PROSPECT = "other_relevant_prospect"


class ProspectPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AuthorityMetric(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    provider: str = "MOZ"
    metric_name: str
    value: float | int | str | None = None
    status: AuthorityStatus = AuthorityStatus.AVAILABLE
    observed_at: datetime = Field(default_factory=utc_now)
    target: str
    scope: AuthorityScope


class AuthorityObservation(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    observation_id: UUID = Field(default_factory=uuid4)
    provider: str = "MOZ"
    target: str
    scope: AuthorityScope
    status: AuthorityStatus = AuthorityStatus.AVAILABLE
    domain_authority: float | None = Field(default=None, ge=0, le=100)
    page_authority: float | None = Field(default=None, ge=0, le=100)
    spam_score: float | None = Field(default=None, ge=-1, le=100)
    link_propensity: float | None = Field(default=None, ge=0)
    http_status: int | None = None
    root_domain: str | None = None
    subdomain: str | None = None
    last_crawled: str | None = None
    pages_to_page: int | None = Field(default=None, ge=0)
    external_pages_to_page: int | None = Field(default=None, ge=0)
    root_domains_to_page: int | None = Field(default=None, ge=0)
    pages_to_root_domain: int | None = Field(default=None, ge=0)
    external_pages_to_root_domain: int | None = Field(default=None, ge=0)
    root_domains_to_root_domain: int | None = Field(default=None, ge=0)
    observed_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="before")
    @classmethod
    def normalize_target(cls, value: object) -> object:
        if not isinstance(value, dict) or not value.get("target"):
            return value
        data = dict(value)
        scope = AuthorityScope(data.get("scope", AuthorityScope.URL))
        data["target"] = normalized_domain(str(data["target"])) if scope is AuthorityScope.DOMAIN else canonical_url(str(data["target"]))
        return data

    def metrics(self) -> tuple[AuthorityMetric, ...]:
        names = ("domain_authority", "page_authority", "spam_score", "link_propensity")
        return tuple(AuthorityMetric(metric_name=name, value=getattr(self, name), status=AuthorityStatus.AVAILABLE if getattr(self, name) is not None else AuthorityStatus.NOT_AVAILABLE, observed_at=self.observed_at, target=self.target, scope=self.scope) for name in names)


class ScoreBreakdown(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    relevance: int = Field(ge=0, le=25)
    authority: int = Field(ge=0, le=20)
    page_authority: int = Field(ge=0, le=10)
    risk_adjustment: int = Field(ge=-20, le=0)
    competitor_gap: int = Field(ge=0, le=15)
    link_intersect: int = Field(ge=0, le=10)
    target_page: int = Field(ge=0, le=10)
    contactability: int = Field(ge=0, le=10)

    @property
    def total(self) -> int:
        return max(0, min(100, self.relevance + self.authority + self.page_authority + self.risk_adjustment + self.competitor_gap + self.link_intersect + self.target_page + self.contactability))


class BacklinkProspect(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    prospect_id: UUID = Field(default_factory=uuid4)
    domain: str
    representative_url: HttpUrl
    opportunity_type: ProspectOpportunityType
    discovery_source: str
    competitors: tuple[str, ...] = ()
    target_page: HttpUrl | None = None
    authority_observation_id: UUID | None = None
    domain_authority: float | None = None
    page_authority: float | None = None
    spam_score: float | None = None
    link_propensity: float | None = None
    relevance: int = Field(default=0, ge=0, le=100)
    contactability: int = Field(default=0, ge=0, le=100)
    score: int = Field(default=0, ge=0, le=100)
    priority: ProspectPriority = ProspectPriority.LOW
    reasons: tuple[str, ...] = ()
    observed_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        if data.get("representative_url"):
            data["representative_url"] = canonical_url(str(data["representative_url"]))
            data["domain"] = normalized_domain(str(data["representative_url"]))
        return data


class LinkIntersectObservation(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_domain: str
    representative_urls: tuple[str, ...]
    competitor_domains: tuple[str, ...]
    competitor_count: int = Field(ge=0)
    target_observed: bool
    evidence_state: ObservedGapState
    authority: AuthorityObservation | None = None
    provenance: tuple[str, ...] = ()


class OutreachHandoff(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    prospect_id: UUID
    domain: str
    representative_url: HttpUrl
    target_page: HttpUrl | None
    opportunity_type: ProspectOpportunityType
    authority_evidence: AuthorityObservation | None
    risk: str
    relevance: int
    score: int
    priority: ProspectPriority
    contactability: int
    discovery_source: str
    evidence_summary: tuple[str, ...]


class AuthorityBatchPreview(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    requested: int
    unique_targets: int
    cached: int
    provider_calls: int
    maximum: int
