"""Replaceable dependency factories for HTTP adapters."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from api.config import APISettings
from src.ai_visibility.repository import AIVisibilityRepository
from src.backlinks.repositories.backlink_repository import BacklinkRepository
from src.research.repositories.prospect_repository import ProspectRepository
from src.seo.repositories.seo_audit_repository import SEOAuditRepository


@dataclass(frozen=True, slots=True)
class DashboardRepositories:
    prospects: ProspectRepository
    backlinks: BacklinkRepository
    seo: SEOAuditRepository
    ai_visibility: AIVisibilityRepository


def dashboard_repositories(request: Request) -> DashboardRepositories:
    """Create repository adapters without constructing external providers."""

    settings: APISettings = request.app.state.settings
    path = settings.database_path
    return DashboardRepositories(
        prospects=ProspectRepository(str(path)),
        backlinks=BacklinkRepository(path),
        seo=SEOAuditRepository(path),
        ai_visibility=AIVisibilityRepository(path),
    )
