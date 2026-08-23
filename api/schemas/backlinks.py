"""Backlink intelligence API contracts."""

from pydantic import BaseModel, ConfigDict

from src.backlinks.domain import AuthorityObservation, Backlink, BacklinkOpportunity, BacklinkProspect
from src.backlinks.domain.intelligence import AuthorityBatchPreview, LinkIntersectObservation


class BacklinkSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backlinks: list[Backlink]
    opportunities: list[BacklinkOpportunity]
    authority: list[AuthorityObservation]
    prospects: list[BacklinkProspect]
    referring_domains: list[dict[str, int | str]]
    prospect_history: list[BacklinkProspect]
    intersect: list[LinkIntersectObservation]
    competitor_gaps: list[LinkIntersectObservation]
    anchors: list[dict[str, object]]
    reclamation: list[dict[str, str]]
    moz_configured: bool


class AuthorityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    targets: list[str]
    scope: str = "url"
    force: bool = False


class AuthorityPreviewResponse(BaseModel):
    preview: AuthorityBatchPreview
