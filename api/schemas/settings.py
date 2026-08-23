"""Credential-safe provider configuration contracts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ProviderStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    status: Literal["CONFIGURED", "MISSING", "OFFLINE_READY"]
    detail: str


class ProviderStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    providers: list[ProviderStatus]
    authentication: Literal["DEFERRED_TO_SAAS_FOUNDATION"] = "DEFERRED_TO_SAAS_FOUNDATION"
