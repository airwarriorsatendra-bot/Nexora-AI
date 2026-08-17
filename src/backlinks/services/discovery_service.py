"""Evidence-preserving backlink opportunity discovery service."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from urllib.parse import urlparse

from src.backlinks.domain.opportunity import BacklinkOpportunity
from src.backlinks.dto.backlink_discovery import BacklinkDiscoveryRequest, BacklinkDiscoveryResponse
from src.backlinks.repositories.backlink_repository import BacklinkRepository
from src.core.enums import BacklinkOpportunityType
from src.core.exceptions import RepositoryError


class BacklinkDiscoveryService:
    """Persist supplied candidate pages as opportunities, not verified links."""

    def __init__(self, repository: BacklinkRepository, logger: logging.Logger | None = None) -> None:
        self._repository = repository
        self._logger = logger or logging.getLogger(__name__)

    async def discover(self, request: BacklinkDiscoveryRequest) -> BacklinkDiscoveryResponse:
        now = datetime.now(UTC)
        opportunities: list[BacklinkOpportunity] = []
        try:
            for candidate in request.candidate_urls:
                value = str(candidate)
                title = urlparse(value).path.replace("-", " ").replace("/", " ").strip()
                opportunity = BacklinkOpportunity(
                    url=value, title=title, opportunity_type=self._classify(value),
                    evidence=("Candidate URL was supplied for backlink investigation.",),
                    source=request.source, discovered_at=now, last_seen=now,
                )
                await self._repository.save_opportunity(opportunity)
                opportunities.append(opportunity)
            return BacklinkDiscoveryResponse(success=True, opportunities=opportunities, message="Backlink opportunities saved. Verify a source page before treating any candidate as a backlink.")
        except RepositoryError as exc:
            self._logger.exception("Backlink opportunity persistence failed.")
            return BacklinkDiscoveryResponse(success=False, errors=[str(exc)], message="Backlink opportunities could not be saved.")

    @staticmethod
    def _classify(url: str) -> BacklinkOpportunityType:
        text = url.lower()
        rules = (("guest", BacklinkOpportunityType.GUEST_POST), ("write-for-us", BacklinkOpportunityType.GUEST_POST), ("resource", BacklinkOpportunityType.RESOURCE_PAGE), ("directory", BacklinkOpportunityType.DIRECTORY), ("listing", BacklinkOpportunityType.DIRECTORY), ("news", BacklinkOpportunityType.NEWS), ("partner", BacklinkOpportunityType.PARTNER), ("blog", BacklinkOpportunityType.BLOG), ("list", BacklinkOpportunityType.LISTICLE))
        return next((kind for token, kind in rules if token in text), BacklinkOpportunityType.OTHER)
