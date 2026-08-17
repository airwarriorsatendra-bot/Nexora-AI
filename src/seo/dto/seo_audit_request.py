"""Validated request for a deterministic single-page SEO audit."""

from __future__ import annotations

from pydantic import ConfigDict, HttpUrl

from src.shared.base.base_model import NexoraModel


class SEOAuditRequest(NexoraModel):
    """Input accepted by SEOAuditService."""

    model_config = ConfigDict(frozen=True, extra="forbid", validate_assignment=True)

    url: HttpUrl
