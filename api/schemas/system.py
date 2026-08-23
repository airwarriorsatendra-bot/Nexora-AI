"""System endpoint schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class SystemStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "ready", "not_ready"]
    service: str
    version: str


class VersionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: str
    version: str


class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ErrorDetail
