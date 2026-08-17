"""Immutable result of one SEO page audit."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import ConfigDict, Field, HttpUrl

from src.seo.domain.seo_issue import SEOIssue
from src.shared.base.base_model import NexoraModel


class SEOAudit(NexoraModel):
    """Persistable, explainable technical and on-page audit result."""

    model_config = ConfigDict(frozen=True, extra="forbid", validate_assignment=True)

    audit_id: UUID = Field(default_factory=uuid4)
    url: HttpUrl
    audited_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    overall_score: float = Field(ge=0, le=100)
    category_scores: dict[str, float] = Field(default_factory=dict)
    issues: list[SEOIssue] = Field(default_factory=list)
    metrics: dict[str, int | str | bool | None] = Field(default_factory=dict)

    @property
    def issue_count(self) -> int:
        return len(self.issues)
