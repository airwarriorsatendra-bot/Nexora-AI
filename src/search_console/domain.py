"""Typed, provenance-preserving Google Search Console records."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from pydantic import ConfigDict, Field, model_validator

from src.shared.base.base_model import NexoraModel


class SearchDimension(str, Enum):
    QUERY = "query"
    PAGE = "page"
    DATE = "date"
    COUNTRY = "country"
    DEVICE = "device"


class ReportingPeriod(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_dates(self) -> "ReportingPeriod":
        if self.end_date < self.start_date:
            raise ValueError("end_date must not precede start_date")
        return self

    @property
    def days(self) -> int:
        return (self.end_date - self.start_date).days + 1


class SearchConsoleProperty(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    site_url: str = Field(min_length=1, max_length=2_048)
    permission_level: str = Field(min_length=1, max_length=128)


class SearchPerformanceRecord(NexoraModel):
    """One normalized row. CTR remains Google's 0-to-1 ratio."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dimensions: tuple[SearchDimension, ...] = ()
    keys: tuple[str, ...] = ()
    clicks: int = Field(ge=0)
    impressions: int = Field(ge=0)
    ctr: Decimal = Field(ge=0, le=1)
    average_position: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def validate_keys(self) -> "SearchPerformanceRecord":
        if len(self.dimensions) != len(self.keys):
            raise ValueError("keys must align with dimensions")
        return self

    def dimension_value(self, dimension: SearchDimension) -> str | None:
        try:
            return self.keys[self.dimensions.index(dimension)]
        except ValueError:
            return None


class SearchPerformanceSnapshot(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    snapshot_id: UUID = Field(default_factory=uuid4)
    property: SearchConsoleProperty
    period: ReportingPeriod
    dimensions: tuple[SearchDimension, ...] = ()
    records: tuple[SearchPerformanceRecord, ...] = ()
    source: str = "GOOGLE_SEARCH_CONSOLE"
    provider: str = "GOOGLE_SEARCH_CONSOLE_API"
    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_records(self) -> "SearchPerformanceSnapshot":
        if any(record.dimensions != self.dimensions for record in self.records):
            raise ValueError("all records must use the snapshot dimensions")
        return self

    @property
    def totals(self) -> SearchPerformanceRecord:
        clicks = sum(record.clicks for record in self.records)
        impressions = sum(record.impressions for record in self.records)
        ctr = Decimal(clicks) / Decimal(impressions) if impressions else Decimal()
        position_weight = sum((record.average_position * record.impressions for record in self.records), Decimal())
        position = position_weight / Decimal(impressions) if impressions else Decimal()
        return SearchPerformanceRecord(clicks=clicks, impressions=impressions, ctr=ctr, average_position=position)
