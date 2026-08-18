"""Immutable, explicit Outreach Automation domain records."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import ConfigDict, EmailStr, Field, HttpUrl

from src.core.enums import CampaignObjective, CampaignStatus, MessageStatus, RecipientStatus
from src.shared.base.base_model import NexoraModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class OutreachCandidate(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    candidate_id: UUID = Field(default_factory=uuid4)
    domain: str = Field(min_length=1, max_length=255)
    website_url: HttpUrl
    contact_name: str = Field(default="", max_length=200)
    email: EmailStr
    source: str = Field(default="manual", max_length=100)
    research_prospect_id: UUID | None = None
    backlink_opportunity_url: HttpUrl | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Campaign(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    campaign_id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2_000)
    objective: CampaignObjective = CampaignObjective.GENERAL
    target_opportunity_type: str | None = None
    owner_context: str = ""
    sequence_id: UUID | None = None
    prospect_count: int = Field(default=0, ge=0)
    provider: str = "fake"
    send_mode: str = "offline"
    status: CampaignStatus = CampaignStatus.DRAFT
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class CampaignRecipient(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    recipient_id: UUID = Field(default_factory=uuid4)
    campaign_id: UUID
    candidate_id: UUID
    status: RecipientStatus = RecipientStatus.PENDING
    sequence_position: int = Field(default=1, ge=1, le=20)
    last_contacted_at: datetime | None = None
    next_followup_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)


class OutreachMessage(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    message_id: UUID = Field(default_factory=uuid4)
    campaign_id: UUID
    recipient_id: UUID
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=20_000)
    sequence_step: int = Field(default=1, ge=1, le=20)
    status: MessageStatus = MessageStatus.PREPARED
    scheduled_at: datetime | None = None
    sent_at: datetime | None = None
    provider_message_id: str | None = None
    provider_thread_id: str | None = None
    provider: str = "fake"
    error_state: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
