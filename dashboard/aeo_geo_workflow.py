"""Short-lived dashboard workflow for AEO/GEO readiness."""
from __future__ import annotations

import os

from dotenv import load_dotenv

from src.aeo_geo.composition import AEOGEOComposition
from src.competitor_gap.composition import CompetitorGapSettings


class AEOGEODashboardWorkflow:
    def __init__(self, factory=None) -> None:
        self.factory = factory or self._build

    @staticmethod
    def _build():
        load_dotenv()
        settings = CompetitorGapSettings.from_environment(dict(os.environ))
        return AEOGEOComposition(settings).build()

    async def targets(self):
        app = self.factory()
        try:
            return await app.targets()
        finally:
            await app.aclose()

    async def analyze(self, target: str):
        app = self.factory()
        try:
            return await app.analyze(target)
        finally:
            await app.aclose()
