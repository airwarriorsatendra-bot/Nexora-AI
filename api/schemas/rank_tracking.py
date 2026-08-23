"""Rank Tracking HTTP contracts preserving SERP and GSC distinctions."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.rank_tracking.domain import CompetitorObservation, Device, RankChange, RankCheck, TrackedKeyword


class AddTrackedKeywordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    keyword: str = Field(min_length=1, max_length=256)
    target_domain: str = Field(min_length=1, max_length=253)
    target_url: str | None = Field(default=None, max_length=2048)
    country: str = Field(default="US", min_length=2, max_length=2)
    device: Device = Device.DESKTOP


class RankCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    depth: int = Field(default=20, ge=1, le=100)


class RankRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    keyword: TrackedKeyword
    latest_check: RankCheck | None = None
    change: RankChange | None = None


class RankTrackingSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    configured: bool
    rows: list[RankRow]
    competitors: list[CompetitorObservation]


class RankCheckResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    checked: int
    results: list[RankCheck]
