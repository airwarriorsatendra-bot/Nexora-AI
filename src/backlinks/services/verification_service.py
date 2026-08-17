"""HTML-evidence-based backlink verification service."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.backlinks.domain.backlink import Backlink
from src.backlinks.domain.normalization import canonical_url
from src.backlinks.dto.backlink_verification import BacklinkVerificationRequest, BacklinkVerificationResponse
from src.backlinks.repositories.backlink_repository import BacklinkRepository
from src.core.enums import BacklinkVerificationStatus, LinkAttribute
from src.core.exceptions import CrawlError, RepositoryError


class BacklinkVerificationService:
    """Verify one exact link; a failed crawl never turns a link into lost."""

    def __init__(self, fetch_html: Callable[[str], Awaitable[str]], repository: BacklinkRepository, logger: logging.Logger | None = None) -> None:
        self._fetch_html = fetch_html
        self._repository = repository
        self._logger = logger or logging.getLogger(__name__)

    async def verify(self, request: BacklinkVerificationRequest) -> BacklinkVerificationResponse:
        source_url, target_url = canonical_url(str(request.source_url)), canonical_url(str(request.target_url))
        existing = await self._repository.find_by_identity(source_url, target_url)
        now = datetime.now(UTC)
        try:
            html = await self._fetch_html(source_url)
        except CrawlError as exc:
            self._logger.warning("Backlink source crawl failed.", extra={"source_url": source_url, "target_url": target_url})
            return BacklinkVerificationResponse(success=False, backlink=existing, errors=[str(exc)], message="Source page could not be crawled; prior verification state was preserved.")
        except Exception as exc:
            self._logger.exception("Backlink source fetch failed.", extra={"source_url": source_url, "target_url": target_url})
            return BacklinkVerificationResponse(success=False, backlink=existing, errors=[str(exc)], message="Source page could not be crawled; prior verification state was preserved.")

        found = self._find_link(html, source_url, target_url)
        if found is not None:
            backlink = Backlink(source_url=source_url, target_url=target_url, anchor_text=found[0], rel=found[1], status=BacklinkVerificationStatus.VERIFIED, first_seen=existing.first_seen if existing else now, last_seen=now, last_verified=now, discovered_at=existing.discovered_at if existing else now)
            message = "Backlink verified from source-page HTML."
        elif existing and existing.status is BacklinkVerificationStatus.VERIFIED:
            backlink = existing.model_copy(update={"status": BacklinkVerificationStatus.LOST, "last_seen": now, "last_verified": now})
            message = "A successful recrawl found that the previously verified link is no longer present."
        else:
            backlink = Backlink(source_url=source_url, target_url=target_url, status=BacklinkVerificationStatus.DISCOVERED, first_seen=existing.first_seen if existing else now, last_seen=now, last_verified=now, discovered_at=existing.discovered_at if existing else now)
            message = "Source page was crawled successfully, but the target link was not found."
        try:
            await self._repository.save(backlink)
        except RepositoryError as exc:
            self._logger.exception("Backlink persistence failed.", extra={"source_url": source_url, "target_url": target_url})
            return BacklinkVerificationResponse(success=False, backlink=backlink, errors=[str(exc)], message="Verification completed but the result could not be saved.")
        return BacklinkVerificationResponse(success=True, backlink=backlink, message=message)

    @staticmethod
    def _find_link(html: str, source_url: str, target_url: str) -> tuple[str, tuple[LinkAttribute, ...]] | None:
        soup = BeautifulSoup(html or "", "lxml")
        for anchor in soup.find_all("a", href=True):
            try:
                destination = canonical_url(urljoin(source_url, str(anchor["href"])))
            except Exception:
                continue
            if destination != target_url:
                continue
            values = {str(value).lower() for value in anchor.get("rel", [])}
            attributes = tuple(attribute for attribute in LinkAttribute if attribute is not LinkAttribute.FOLLOW and attribute.value in values)
            if not attributes:
                attributes = (LinkAttribute.FOLLOW,)
            return anchor.get_text(" ", strip=True), attributes
        return None
