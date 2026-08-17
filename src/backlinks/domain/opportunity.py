"""Immutable backlink-opportunity domain entity."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import ConfigDict, Field, HttpUrl, model_validator

from src.backlinks.domain.normalization import canonical_url, normalized_domain
from src.core.enums import BacklinkOpportunityStatus, BacklinkOpportunityType
from src.shared.base.base_model import NexoraModel


class BacklinkOpportunity(NexoraModel):
    """A candidate page worth investigating, never a claimed backlink."""

    model_config = ConfigDict(frozen=True, extra="forbid", validate_assignment=True)

    opportunity_id: UUID = Field(default_factory=uuid4)
    url: HttpUrl
    domain: str = ""
    title: str = Field(default="", max_length=500)
    description: str = Field(default="", max_length=5_000)
    opportunity_type: BacklinkOpportunityType = BacklinkOpportunityType.OTHER
    evidence: tuple[str, ...] = ()
    source: str = Field(default="user_import", max_length=100)
    status: BacklinkOpportunityStatus = BacklinkOpportunityStatus.NEW
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="before")
    @classmethod
    def _normalize_identity(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        if data.get("url"):
            data["url"] = canonical_url(str(data["url"]))
            data["domain"] = normalized_domain(str(data["url"]))
        return data
