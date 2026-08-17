"""Immutable, provenance-preserving Analytics domain records."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from pydantic import ConfigDict, Field, model_validator

from src.shared.base.base_model import NexoraModel


class Period(NexoraModel):
    """An inclusive, explicitly labelled reporting period."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    date_from: date
    date_to: date

    @model_validator(mode="after")
    def validate_dates(self) -> "Period":
        if self.date_to < self.date_from:
            raise ValueError("date_to must not precede date_from")
        return self


class ChannelKPI(NexoraModel):
    """A metric retaining the source record, unit, currency, and period."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    value: Decimal | int | float | str
    unit: str = Field(min_length=1)
    source_module: str = Field(min_length=1)
    source_system: str = Field(min_length=1)
    period: Period
    source_record_id: str | None = None
    currency: str | None = None

    @model_validator(mode="after")
    def validate_money(self) -> "ChannelKPI":
        """Keep persisted monetary values decimal and explicitly currency-labelled."""
        if self.unit == "money":
            if not isinstance(self.value, Decimal):
                raise ValueError("money KPI values must use Decimal")
            if not self.currency:
                raise ValueError("money KPIs must include a currency")
        return self


class AnalyticsInsight(NexoraModel):
    """A deterministic finding with its supporting evidence."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    insight_id: UUID = Field(default_factory=uuid4)
    category: str = Field(min_length=1)
    priority: str = "MEDIUM"
    title: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    recommendation: str = Field(min_length=1)
    confidence: Decimal = Field(ge=0, le=1)
    source_modules: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AnalyticsReport(NexoraModel):
    """An immutable report snapshot; its KPIs can use source-specific periods."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    report_id: UUID = Field(default_factory=uuid4)
    period: Period
    kpis: list[ChannelKPI] = Field(default_factory=list)
    insights: list[AnalyticsInsight] = Field(default_factory=list)
    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
