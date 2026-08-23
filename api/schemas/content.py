"""Current Content Intelligence request and target contracts."""

from pydantic import BaseModel, ConfigDict, Field
from api.schemas.pagination import PageMetadata


class ContentTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    target_domain: str
    keyword: str
    mapped_page: str | None = None


class ContentBriefRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_domain: str = Field(min_length=1, max_length=253)
    keyword: str = Field(min_length=1, max_length=256)

class ContentTargetPage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[ContentTarget]
    pagination: PageMetadata
