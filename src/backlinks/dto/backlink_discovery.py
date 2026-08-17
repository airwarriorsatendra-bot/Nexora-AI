"""DTOs for deterministic backlink opportunity discovery."""

from __future__ import annotations

from pydantic import ConfigDict, Field, HttpUrl

from src.backlinks.domain.opportunity import BacklinkOpportunity
from src.shared.base.base_model import NexoraModel


class BacklinkDiscoveryRequest(NexoraModel):
    """Candidate URLs supplied by a user or an injected discovery adapter."""

    model_config = ConfigDict(frozen=True, extra="forbid", validate_assignment=True)

    target_url: HttpUrl
    candidate_urls: list[HttpUrl] = Field(min_length=1, max_length=100)
    source: str = Field(default="user_import", min_length=1, max_length=100)


class BacklinkDiscoveryResponse(NexoraModel):
    """Persisted opportunity result, without asserting backlink existence."""

    success: bool
    opportunities: list[BacklinkOpportunity] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    message: str = ""
