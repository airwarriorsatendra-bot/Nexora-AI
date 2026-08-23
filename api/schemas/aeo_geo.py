from pydantic import BaseModel, ConfigDict, Field

class AEOGEOBriefRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    target_domain: str = Field(min_length=1, max_length=253)
    query: str = Field(min_length=1, max_length=256)
