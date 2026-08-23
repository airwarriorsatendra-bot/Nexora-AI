"""HTTP request and response contracts for AI Visibility."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.ai_visibility.domain import (
    AIVisibilityObservation,
    MonitoredPrompt,
    ProviderCapability,
    VisibilityReport,
)


class AddPromptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    text: str = Field(min_length=1, max_length=4000)


class VisibilityRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    brand_name: str = Field(min_length=1, max_length=200)
    target_domain: str = Field(min_length=1, max_length=253)
    prompt_ids: list[str] = Field(min_length=1, max_length=25)
    provider_names: list[str] = Field(min_length=1, max_length=3)
    repetitions: int = Field(default=1, ge=1, le=3)
    brand_aliases: list[str] = Field(default_factory=list, max_length=20)
    competitors: dict[str, list[str]] = Field(default_factory=dict)


class VisibilityRunPreview(BaseModel):
    prompts: int
    providers: int
    repetitions: int
    total_api_calls: int


class AIVisibilitySnapshot(BaseModel):
    providers: list[ProviderCapability]
    prompts: list[MonitoredPrompt]
    history: list[AIVisibilityObservation]


class VisibilityRunResponse(BaseModel):
    preview: VisibilityRunPreview
    report: VisibilityReport
