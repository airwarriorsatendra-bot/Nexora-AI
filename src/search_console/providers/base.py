"""Provider boundary isolated from Google HTTP details."""

from __future__ import annotations

from typing import Protocol

from src.search_console.domain import SearchConsoleProperty, SearchPerformanceRecord
from src.search_console.dto import SearchAnalyticsRequest


class SearchConsoleProvider(Protocol):
    async def list_properties(self) -> tuple[SearchConsoleProperty, ...]: ...
    async def query_search_analytics(self, request: SearchAnalyticsRequest) -> tuple[SearchPerformanceRecord, ...]: ...
    async def aclose(self) -> None: ...
