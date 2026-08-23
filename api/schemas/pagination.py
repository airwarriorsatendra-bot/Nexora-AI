"""Shared deterministic page/limit response metadata."""

from pydantic import BaseModel, ConfigDict, Field


class PageMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int = Field(ge=1)
    limit: int = Field(ge=1, le=100)
    returned: int = Field(ge=0)
    has_more: bool
