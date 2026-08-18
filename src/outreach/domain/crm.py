"""Typed CRM, contact, sequence, reply, and audit records for Outreach Beta 15."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import ConfigDict, EmailStr, Field, HttpUrl

from src.shared.base.base_model import NexoraModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class CRMState(str, Enum):
    NEW="new"; RESEARCHING="researching"; CONTACT_FOUND="contact_found"; READY_FOR_OUTREACH="ready_for_outreach"; IN_CAMPAIGN="in_campaign"; CONTACTED="contacted"; FOLLOW_UP_DUE="follow_up_due"; REPLIED="replied"; POSITIVE_REPLY="positive_reply"; NEGATIVE_REPLY="negative_reply"; NO_RESPONSE="no_response"; BOUNCED="bounced"; UNSUBSCRIBED="unsubscribed"; DO_NOT_CONTACT="do_not_contact"; WON="won"; LOST="lost"; ARCHIVED="archived"


class VerificationState(str, Enum):
    VERIFIED="verified"; UNVERIFIED="unverified"; RISKY="risky"; INVALID="invalid"; UNKNOWN="unknown"; PROVIDER_ERROR="provider_error"


class ReplyClassification(str, Enum):
    POSITIVE="positive"; NEGATIVE="negative"; QUESTION="question"; UNSUBSCRIBE="unsubscribe"; AUTO_REPLY="auto_reply"; UNKNOWN="unknown"


class OutreachProspect(NexoraModel):
    model_config=ConfigDict(frozen=True,extra="forbid")
    prospect_id: UUID
    domain: str
    representative_url: HttpUrl
    target_page: HttpUrl | None=None
    opportunity_type: str
    moz_domain_authority: float | None=None
    moz_page_authority: float | None=None
    moz_spam_score: float | None=None
    risk: str
    relevance: int=Field(ge=0,le=100)
    score: int=Field(ge=0,le=100)
    priority: str
    contactability: int=Field(ge=0,le=100)
    discovery_source: str
    evidence_summary: tuple[str,...]=()
    technical_preconditions: tuple[str,...]=()
    state: CRMState=CRMState.NEW
    last_action_at: datetime=Field(default_factory=utc_now)


class OutreachContact(NexoraModel):
    model_config=ConfigDict(frozen=True,extra="forbid")
    contact_id: UUID=Field(default_factory=uuid4)
    prospect_id: UUID | None=None
    name: str=""
    role: str=""
    email: EmailStr
    domain: str
    source: str="manual"
    source_url: HttpUrl | None=None
    confidence: float | None=Field(default=None,ge=0,le=1)
    verification_state: VerificationState=VerificationState.UNVERIFIED
    discovery_provider: str="manual"
    observed_at: datetime=Field(default_factory=utc_now)
    last_contacted_at: datetime | None=None


class OutreachSequence(NexoraModel):
    model_config=ConfigDict(frozen=True,extra="forbid")
    sequence_id: UUID=Field(default_factory=uuid4)
    name: str=Field(min_length=1,max_length=200)
    status: str="draft"
    created_at: datetime=Field(default_factory=utc_now)


class SequenceStep(NexoraModel):
    model_config=ConfigDict(frozen=True,extra="forbid")
    step_id: UUID=Field(default_factory=uuid4)
    sequence_id: UUID
    step_number: int=Field(ge=1,le=20)
    delay_days: int=Field(default=0,ge=0,le=90)
    subject_template: str=Field(min_length=1,max_length=300)
    body_template: str=Field(min_length=1,max_length=20_000)
    condition: str="no_reply"
    stop_on_reply: bool=True


class OutreachReply(NexoraModel):
    model_config=ConfigDict(frozen=True,extra="forbid")
    reply_id: UUID=Field(default_factory=uuid4)
    message_id: UUID
    received_at: datetime=Field(default_factory=utc_now)
    provider_message_id: str | None=None
    provider_thread_id: str | None=None
    classification: ReplyClassification=ReplyClassification.UNKNOWN
    provider: str="manual"
    sender: str=""
    recipient: str=""
    subject: str=""
    snippet: str=""
    observed_at: datetime=Field(default_factory=utc_now)


class OutreachHistoryEvent(NexoraModel):
    model_config=ConfigDict(frozen=True,extra="forbid")
    event_id: UUID=Field(default_factory=uuid4)
    entity_type: str
    entity_id: UUID
    event_type: str
    detail: str=""
    occurred_at: datetime=Field(default_factory=utc_now)


class CampaignAnalytics(NexoraModel):
    prospects:int=0; contacts:int=0; sent:int=0; failed:int=0; bounced:int=0; replies:int=0; positive_replies:int=0; negative_replies:int=0
    @property
    def reply_rate(self)->float:return self.replies/self.sent if self.sent else 0.0
    @property
    def positive_reply_rate(self)->float:return self.positive_replies/self.sent if self.sent else 0.0
    @property
    def bounce_rate(self)->float:return self.bounced/self.sent if self.sent else 0.0
