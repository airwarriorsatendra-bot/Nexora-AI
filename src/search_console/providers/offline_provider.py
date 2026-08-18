"""Deterministic injected provider for offline tests and unconfigured UI."""

from __future__ import annotations

from src.core.exceptions import ConfigurationError
from src.search_console.domain import SearchConsoleProperty, SearchPerformanceRecord
from src.search_console.dto import SearchAnalyticsRequest


class OfflineSearchConsoleProvider:
    def __init__(self, *, properties: tuple[SearchConsoleProperty, ...] = (), records: dict[tuple[str, tuple[str, ...]], tuple[SearchPerformanceRecord, ...]] | None = None, error: Exception | None = None) -> None:
        self._properties = properties
        self._records = records or {}
        self._error = error
        self.closed = False

    async def list_properties(self) -> tuple[SearchConsoleProperty, ...]:
        if self._error:
            raise self._error
        return self._properties

    async def query_search_analytics(self, request: SearchAnalyticsRequest) -> tuple[SearchPerformanceRecord, ...]:
        if self._error:
            raise self._error
        key = (request.property.site_url, tuple(item.value for item in request.dimensions))
        return self._records.get(key, ())[:request.row_limit]

    async def aclose(self) -> None:
        self.closed = True


class UnconfiguredSearchConsoleProvider(OfflineSearchConsoleProvider):
    async def list_properties(self) -> tuple[SearchConsoleProperty, ...]:
        raise ConfigurationError("Google Search Console is not configured.")

    async def query_search_analytics(self, request: SearchAnalyticsRequest) -> tuple[SearchPerformanceRecord, ...]:
        del request
        raise ConfigurationError("Google Search Console is not configured.")
