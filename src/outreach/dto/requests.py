"""Validated application inputs for Outreach operations."""

from __future__ import annotations

from uuid import UUID

from pydantic import ConfigDict, EmailStr, Field, HttpUrl

from src.core.enums import CampaignObjective
from src.shared.base.base_model import NexoraModel


class CreateCampaignRequest(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2_000)
    objective: CampaignObjective = CampaignObjective.GENERAL


class AddCandidateRequest(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    website_url: HttpUrl
    email: EmailStr
    contact_name: str = Field(default="", max_length=200)
    source: str = Field(default="manual", max_length=100)
    research_prospect_id: UUID | None = None
    backlink_opportunity_url: HttpUrl | None = None


class AddRecipientRequest(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    campaign_id: UUID
    candidate_id: UUID
    sequence_position: int = Field(default=1, ge=1, le=20)


class PrepareMessageRequest(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    campaign_id: UUID
    recipient_id: UUID
    subject_template: str = Field(min_length=1, max_length=300)
    body_template: str = Field(min_length=1, max_length=20_000)
    sequence_step: int = Field(default=1, ge=1, le=20)
    followup_delay_days: int = Field(default=3, ge=1, le=90)


class SendMessageRequest(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    message_id: UUID
    dry_run: bool = True
