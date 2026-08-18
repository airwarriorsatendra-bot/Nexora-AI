"""Typed GA4 records retaining source metric semantics."""
from __future__ import annotations
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4
from pydantic import ConfigDict, Field, model_validator
from src.shared.base.base_model import NexoraModel
class GA4Dimension(str, Enum):
    DATE="date"; CHANNEL="sessionDefaultChannelGroup"; LANDING_PAGE="landingPagePlusQueryString"; EVENT="eventName"; DEVICE="deviceCategory"; COUNTRY="country"
class ReportingPeriod(NexoraModel):
    model_config=ConfigDict(frozen=True,extra="forbid")
    start_date: date; end_date: date
    @model_validator(mode="after")
    def valid(self):
        if self.end_date < self.start_date: raise ValueError("end_date must not precede start_date")
        return self
class GA4Property(NexoraModel):
    model_config=ConfigDict(frozen=True,extra="forbid")
    property_id: str=Field(min_length=1); display_name: str=""; account_id: str|None=None; account_name: str|None=None
class GA4Record(NexoraModel):
    model_config=ConfigDict(frozen=True,extra="forbid")
    dimensions: tuple[GA4Dimension,...]=(); keys: tuple[str,...]=(); metrics: dict[str,Decimal]=Field(default_factory=dict)
    @model_validator(mode="after")
    def valid(self):
        if len(self.dimensions)!=len(self.keys): raise ValueError("keys must align with dimensions")
        if any(value<0 for value in self.metrics.values()): raise ValueError("metrics cannot be negative")
        return self
class GA4Snapshot(NexoraModel):
    model_config=ConfigDict(frozen=True,extra="forbid")
    snapshot_id: UUID=Field(default_factory=uuid4); property: GA4Property; period: ReportingPeriod; dimensions: tuple[GA4Dimension,...]=(); metrics: tuple[str,...]=(); records: tuple[GA4Record,...]=(); source: str="GOOGLE_ANALYTICS_4"; provider: str="GOOGLE_ANALYTICS_DATA_API"; captured_at: datetime=Field(default_factory=lambda:datetime.now(UTC))
    @property
    def totals(self): return {name:sum((record.metrics.get(name,Decimal()) for record in self.records),Decimal()) for name in self.metrics}
