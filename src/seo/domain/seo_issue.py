"""Structured, deterministic SEO finding."""

from __future__ import annotations

from src.core.enums import Priority
from src.shared.base.base_model import NexoraModel


class SEOIssue(NexoraModel):
    """One actionable issue discovered while auditing a page."""

    code: str
    category: str
    severity: Priority
    title: str
    description: str
    evidence: str = ""
    recommendation: str = ""
    affected_url: str = ""
