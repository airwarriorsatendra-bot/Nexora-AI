"""Response returned by the SEO audit application service."""

from __future__ import annotations

from src.seo.domain.seo_audit import SEOAudit
from src.shared.base.base_model import NexoraModel


class SEOAuditResponse(NexoraModel):
    """Stable response shape for dashboard and future API consumers."""

    success: bool
    audit: SEOAudit | None = None
    errors: list[str] = []
    message: str = ""
