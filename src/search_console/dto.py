"""Input and output DTOs for Google Search Console operations."""

from __future__ import annotations

from pydantic import ConfigDict, Field

from src.search_console.domain import ReportingPeriod, SearchConsoleProperty, SearchDimension, SearchPerformanceRecord, SearchPerformanceSnapshot
from src.shared.base.base_model import NexoraModel


class SearchAnalyticsRequest(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    property: SearchConsoleProperty
    period: ReportingPeriod
    dimensions: tuple[SearchDimension, ...] = ()
    row_limit: int = Field(default=1_000, ge=1, le=25_000)


class SearchPerformanceResponse(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    snapshot: SearchPerformanceSnapshot
    top_queries: tuple[SearchPerformanceRecord, ...] = ()
    top_pages: tuple[SearchPerformanceRecord, ...] = ()
    date_records: tuple[SearchPerformanceRecord, ...] = ()
    ctr_opportunities: tuple[SearchPerformanceRecord, ...] = ()
    position_opportunities: tuple[SearchPerformanceRecord, ...] = ()
