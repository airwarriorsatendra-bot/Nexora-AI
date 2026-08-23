"""Executive dashboard contracts backed by persisted evidence."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DashboardMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    value: int | float | None
    availability: Literal["available", "unavailable"]
    description: str
    source: str


class ActivityItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    title: str
    detail: str
    observed_at: datetime | None = None


class DashboardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metrics: list[DashboardMetric] = Field(max_length=12)
    recent_activity: list[ActivityItem] = Field(max_length=20)
    attention_count: int = Field(ge=0)
