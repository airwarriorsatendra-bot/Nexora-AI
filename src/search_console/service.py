"""Deterministic, evidence-backed Search Console performance intelligence."""

from __future__ import annotations

from decimal import Decimal

from src.core.exceptions import SearchConsoleError
from src.search_console.domain import SearchConsoleProperty, SearchDimension, SearchPerformanceRecord, SearchPerformanceSnapshot
from src.search_console.dto import SearchAnalyticsRequest, SearchPerformanceResponse
from src.search_console.providers.base import SearchConsoleProvider
from src.search_console.repository import SearchConsoleRepository


class SearchPerformanceService:
    def __init__(self, provider: SearchConsoleProvider, repository: SearchConsoleRepository) -> None:
        self._provider, self._repository = provider, repository

    async def list_properties(self) -> tuple[SearchConsoleProperty, ...]:
        return await self._provider.list_properties()

    async def refresh(self, *, property: SearchConsoleProperty, request: SearchAnalyticsRequest) -> SearchPerformanceResponse:
        if request.property != property:
            raise SearchConsoleError("Search Console request property does not match the selected property.")
        snapshots: dict[tuple[SearchDimension, ...], SearchPerformanceSnapshot] = {}
        for dimensions in ((), (SearchDimension.QUERY,), (SearchDimension.PAGE,), (SearchDimension.DATE,)):
            query = request.model_copy(update={"dimensions": dimensions})
            records = await self._provider.query_search_analytics(query)
            snapshot = SearchPerformanceSnapshot(property=property, period=request.period, dimensions=dimensions, records=records)
            await self._repository.save(snapshot)
            snapshots[dimensions] = snapshot
        query_records = snapshots[(SearchDimension.QUERY,)].records
        page_records = snapshots[(SearchDimension.PAGE,)].records
        return SearchPerformanceResponse(snapshot=snapshots[()], top_queries=self.top_records(query_records), top_pages=self.top_records(page_records), date_records=snapshots[(SearchDimension.DATE,)].records, ctr_opportunities=self.ctr_opportunities((*query_records, *page_records)), position_opportunities=self.position_opportunities((*query_records, *page_records)))

    @staticmethod
    def top_records(records: tuple[SearchPerformanceRecord, ...], limit: int = 25) -> tuple[SearchPerformanceRecord, ...]:
        return tuple(sorted(records, key=lambda record: (record.clicks, record.impressions), reverse=True)[:limit])

    @staticmethod
    def ctr_opportunities(records: tuple[SearchPerformanceRecord, ...]) -> tuple[SearchPerformanceRecord, ...]:
        populated = [record for record in records if record.impressions > 0]
        if not populated:
            return ()
        impressions_floor = sorted(record.impressions for record in populated)[len(populated) // 2]
        ctr_ceiling = sorted(record.ctr for record in populated)[max(0, len(populated) // 4 - 1)]
        return tuple(sorted((record for record in populated if record.impressions >= impressions_floor and record.ctr <= ctr_ceiling), key=lambda record: record.impressions, reverse=True))

    @staticmethod
    def position_opportunities(records: tuple[SearchPerformanceRecord, ...]) -> tuple[SearchPerformanceRecord, ...]:
        populated = [record for record in records if record.impressions > 0]
        if not populated:
            return ()
        impressions_floor = sorted(record.impressions for record in populated)[len(populated) // 2]
        return tuple(sorted((record for record in populated if record.impressions >= impressions_floor and Decimal("4") <= record.average_position <= Decimal("20")), key=lambda record: (record.average_position, -record.impressions)))

    @staticmethod
    def compare(current: SearchPerformanceSnapshot, previous: SearchPerformanceSnapshot) -> dict[str, Decimal | int | None]:
        if current.property.site_url != previous.property.site_url or current.dimensions != previous.dimensions or current.period.days != previous.period.days:
            raise SearchConsoleError("Only snapshots for the same property, dimensions, and period length can be compared.")
        current_total, previous_total = current.totals, previous.totals
        return {"clicks": current_total.clicks - previous_total.clicks, "impressions": current_total.impressions - previous_total.impressions, "ctr": current_total.ctr - previous_total.ctr, "average_position": current_total.average_position - previous_total.average_position}
