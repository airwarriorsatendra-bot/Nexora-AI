"""DTOs for source-page backlink verification."""

from __future__ import annotations

from pydantic import ConfigDict, Field, HttpUrl

from src.backlinks.domain.backlink import Backlink
from src.shared.base.base_model import NexoraModel


class BacklinkVerificationRequest(NexoraModel):
    """A specific source page and target URL to verify from HTML evidence."""

    model_config = ConfigDict(frozen=True, extra="forbid", validate_assignment=True)

    source_url: HttpUrl
    target_url: HttpUrl


class BacklinkVerificationResponse(NexoraModel):
    """Verification outcome that distinguishes absence from crawl failure."""

    success: bool
    backlink: Backlink | None = None
    errors: list[str] = Field(default_factory=list)
    message: str = ""
