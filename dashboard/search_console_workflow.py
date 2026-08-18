"""Dashboard adapter for the Search Console composition root."""

from __future__ import annotations

import os
from collections.abc import Callable

from dotenv import load_dotenv

from src.search_console.composition import SearchConsoleApplication, SearchConsoleComposition, SearchConsoleSettings
from src.search_console.domain import SearchConsoleProperty
from src.search_console.dto import SearchAnalyticsRequest, SearchPerformanceResponse


class SearchConsoleDashboardWorkflow:
    def __init__(self, factory: Callable[[], SearchConsoleApplication] | None = None) -> None:
        self._factory = factory or self._build_application

    def is_configured(self) -> bool:
        application = self._factory()
        return application.settings.configured

    async def discover_properties(self) -> tuple[SearchConsoleProperty, ...]:
        application = self._factory()
        try:
            return await application.service.list_properties()
        finally:
            await application.aclose()

    async def refresh(self, request: SearchAnalyticsRequest) -> SearchPerformanceResponse:
        application = self._factory()
        try:
            return await application.service.refresh(property=request.property, request=request)
        finally:
            await application.aclose()

    @staticmethod
    def _build_application() -> SearchConsoleApplication:
        load_dotenv()
        return SearchConsoleComposition(SearchConsoleSettings.from_environment(dict(os.environ))).build()
