"""Immutable verified-link domain entity."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import ConfigDict, Field, HttpUrl, model_validator

from src.backlinks.domain.normalization import canonical_url, normalized_domain
from src.core.enums import BacklinkVerificationStatus, LinkAttribute
from src.shared.base.base_model import NexoraModel


class Backlink(NexoraModel):
    """An observed source-page link to a concrete target URL."""

    model_config = ConfigDict(frozen=True, extra="forbid", validate_assignment=True)

    backlink_id: UUID = Field(default_factory=uuid4)
    source_url: HttpUrl
    target_url: HttpUrl
    source_domain: str = ""
    target_domain: str = ""
    anchor_text: str = Field(default="", max_length=2_000)
    rel: tuple[LinkAttribute, ...] = ()
    status: BacklinkVerificationStatus = BacklinkVerificationStatus.DISCOVERED
    first_seen: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_verified: datetime | None = None
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="before")
    @classmethod
    def _normalize_identity(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        for field in ("source_url", "target_url"):
            if field in data:
                data[field] = canonical_url(str(data[field]))
        if data.get("source_url"):
            data["source_domain"] = normalized_domain(str(data["source_url"]))
        if data.get("target_url"):
            data["target_domain"] = normalized_domain(str(data["target_url"]))
        raw_rel = data.get("rel", ())
        values = {str(item).lower().replace("linkattribute.", "") for item in raw_rel}
        attributes = [attribute for attribute in LinkAttribute if attribute.value in values]
        if LinkAttribute.NOFOLLOW not in attributes and LinkAttribute.FOLLOW not in attributes:
            attributes.insert(0, LinkAttribute.FOLLOW)
        data["rel"] = tuple(attributes)
        return data

    @property
    def is_verified(self) -> bool:
        return self.status is BacklinkVerificationStatus.VERIFIED
