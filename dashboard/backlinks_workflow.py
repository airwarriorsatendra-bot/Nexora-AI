"""Dashboard adapter for the source-layer Backlink Intelligence graph."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from src.backlinks.composition import BacklinkApplication, BacklinkComposition, BacklinkSettings
from src.backlinks.dto.backlink_discovery import BacklinkDiscoveryRequest, BacklinkDiscoveryResponse
from src.backlinks.dto.backlink_verification import BacklinkVerificationRequest, BacklinkVerificationResponse


class BacklinksDashboardWorkflow:
    """Map dashboard forms to closeable source-layer application operations."""

    def __init__(self, application_factory: Callable[[], BacklinkApplication] | None = None) -> None:
        self._application_factory = application_factory or self._build_application

    async def discover(self, target_url: str, candidates: list[str]) -> BacklinkDiscoveryResponse:
        application = self._application_factory()
        try:
            return await application.discovery_service.discover(BacklinkDiscoveryRequest(target_url=target_url, candidate_urls=candidates))
        finally:
            await application.aclose()

    async def verify(self, source_url: str, target_url: str) -> BacklinkVerificationResponse:
        application = self._application_factory()
        try:
            return await application.verification_service.verify(BacklinkVerificationRequest(source_url=source_url, target_url=target_url))
        finally:
            await application.aclose()

    async def list_backlinks(self, target_domain: str):
        application = self._application_factory()
        try:
            return await application.repository.list_backlinks(target_domain=target_domain, limit=500)
        finally:
            await application.aclose()

    @staticmethod
    def _build_application() -> BacklinkApplication:
        return BacklinkComposition(BacklinkSettings.from_environment()).build()


def backlinks_to_dataframe(backlinks: list[object]) -> pd.DataFrame:
    """Serialize source-layer links for safe tabular display and CSV export."""
    return pd.DataFrame([backlink.model_dump(mode="json") for backlink in backlinks])
