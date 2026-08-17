"""Campaign, template, safety, and explicit-delivery orchestration."""

from __future__ import annotations

import logging
import re
from datetime import timedelta
from urllib.parse import urlparse
from uuid import UUID

from src.core.enums import CampaignStatus, DeliveryAttemptStatus, MessageStatus, RecipientStatus, SuppressionReason
from src.core.exceptions import OutreachError, RepositoryError
from src.outreach.domain.models import Campaign, CampaignRecipient, OutreachCandidate, OutreachMessage, utc_now
from src.outreach.dto.requests import AddCandidateRequest, AddRecipientRequest, CreateCampaignRequest, PrepareMessageRequest, SendMessageRequest
from src.outreach.providers.delivery import OutreachDeliveryProvider
from src.outreach.repositories.outreach_repository import OutreachAutomationRepository


class OutreachService:
    """Safe workflow: create/prepare/validate/explicit-send, with no hidden delivery."""

    _VARIABLE = re.compile(r"{{\s*([a-z_]+)\s*}}")
    _TRANSITIONS = {
        CampaignStatus.DRAFT: {CampaignStatus.READY, CampaignStatus.CANCELLED},
        CampaignStatus.READY: {CampaignStatus.ACTIVE, CampaignStatus.PAUSED, CampaignStatus.CANCELLED},
        CampaignStatus.ACTIVE: {CampaignStatus.PAUSED, CampaignStatus.COMPLETED, CampaignStatus.CANCELLED},
        CampaignStatus.PAUSED: {CampaignStatus.ACTIVE, CampaignStatus.CANCELLED},
        CampaignStatus.COMPLETED: set(), CampaignStatus.CANCELLED: set(),
    }

    def __init__(self, repository: OutreachAutomationRepository, delivery_provider: OutreachDeliveryProvider, logger: logging.Logger | None = None) -> None:
        self._repository, self._delivery = repository, delivery_provider
        self._logger = logger or logging.getLogger(__name__)

    async def add_candidate(self, request: AddCandidateRequest) -> OutreachCandidate:
        existing = await self._repository.find_candidate_by_email(str(request.email))
        if existing: return existing
        host = urlparse(str(request.website_url)).hostname or ""
        candidate = OutreachCandidate(domain=host.lower().removeprefix("www."), website_url=request.website_url, email=request.email, contact_name=request.contact_name, source=request.source, research_prospect_id=request.research_prospect_id, backlink_opportunity_url=request.backlink_opportunity_url)
        return await self._repository.save_candidate(candidate)

    async def create_campaign(self, request: CreateCampaignRequest) -> Campaign:
        return await self._repository.save_campaign(Campaign(name=request.name, description=request.description, objective=request.objective))

    async def transition_campaign(self, campaign_id: UUID, target: CampaignStatus) -> Campaign:
        campaign = await self._require_campaign(campaign_id)
        if target not in self._TRANSITIONS[campaign.status]:
            raise OutreachError(f"Campaign cannot transition from {campaign.status.value} to {target.value}.")
        return await self._repository.save_campaign(campaign.model_copy(update={"status": target, "updated_at": utc_now()}))

    async def add_recipient(self, request: AddRecipientRequest) -> CampaignRecipient:
        await self._require_campaign(request.campaign_id)
        if await self._repository.get_candidate(request.candidate_id) is None: raise OutreachError("Outreach candidate was not found.")
        existing = await self._repository.find_recipient(request.campaign_id, request.candidate_id)
        if existing: return existing
        recipient = CampaignRecipient(campaign_id=request.campaign_id, candidate_id=request.candidate_id, sequence_position=request.sequence_position)
        return await self._repository.save_recipient(recipient)

    async def prepare_message(self, request: PrepareMessageRequest) -> OutreachMessage:
        campaign, recipient, candidate = await self._context(request.campaign_id, request.recipient_id)
        if campaign.status not in {CampaignStatus.DRAFT, CampaignStatus.READY, CampaignStatus.ACTIVE, CampaignStatus.PAUSED}: raise OutreachError("This campaign cannot prepare new messages.")
        existing = await self._repository.find_message(campaign.campaign_id, recipient.recipient_id, request.sequence_step)
        if existing: return existing
        subject, body = self._render(request.subject_template, candidate), self._render(request.body_template, candidate)
        message = OutreachMessage(campaign_id=campaign.campaign_id, recipient_id=recipient.recipient_id, subject=subject, body=body, sequence_step=request.sequence_step, scheduled_at=utc_now() + timedelta(days=request.followup_delay_days) if request.sequence_step > 1 else None)
        return await self._repository.save_message(message)

    async def send(self, request: SendMessageRequest) -> OutreachMessage:
        message = await self._require_message(request.message_id)
        campaign, recipient, candidate = await self._context(message.campaign_id, message.recipient_id)
        if not request.dry_run and campaign.status not in {CampaignStatus.READY, CampaignStatus.ACTIVE}: raise OutreachError("Campaign must be ready or active before an explicit send.")
        if recipient.status in {RecipientStatus.REPLIED, RecipientStatus.SUPPRESSED, RecipientStatus.BOUNCED, RecipientStatus.REMOVED}: raise OutreachError("Recipient state blocks delivery.")
        if await self._repository.is_suppressed(str(candidate.email)):
            await self._repository.save_recipient(recipient.model_copy(update={"status": RecipientStatus.SUPPRESSED}))
            raise OutreachError("Recipient is suppressed and cannot receive outreach.")
        if message.sequence_step > 1 and recipient.status is not RecipientStatus.SENT: raise OutreachError("Follow-up requires a successful prior contact.")
        if await self._repository.sent_attempt_exists(message.message_id): return message.model_copy(update={"status": MessageStatus.SENT})
        if request.dry_run:
            await self._repository.save_attempt(message.message_id, self._delivery.provider_name, DeliveryAttemptStatus.SIMULATED.value)
            return await self._repository.save_message(message.model_copy(update={"status": MessageStatus.DRY_RUN}))
        result = await self._delivery.send(recipient=str(candidate.email), subject=message.subject, body=message.body, idempotency_key=f"{message.campaign_id}:{message.recipient_id}:{message.sequence_step}")
        if result.accepted:
            sent = message.model_copy(update={"status": MessageStatus.SENT, "sent_at": utc_now(), "provider_message_id": result.provider_message_id})
            await self._repository.save_attempt(message.message_id, self._delivery.provider_name, DeliveryAttemptStatus.ACCEPTED.value, result.provider_message_id)
            await self._repository.save_recipient(recipient.model_copy(update={"status": RecipientStatus.SENT, "last_contacted_at": sent.sent_at, "next_followup_at": sent.sent_at + timedelta(days=3)}))
            return await self._repository.save_message(sent)
        status = DeliveryAttemptStatus.RATE_LIMITED.value if result.rate_limited else DeliveryAttemptStatus.FAILED.value
        await self._repository.save_attempt(message.message_id, self._delivery.provider_name, status, error_code=result.error_code, error_message=result.error_message)
        return await self._repository.save_message(message.model_copy(update={"status": MessageStatus.FAILED}))

    async def suppress(self, email: str, reason: SuppressionReason) -> None: await self._repository.suppress(email, reason)
    async def list_messages(self, campaign_id: UUID) -> list[OutreachMessage]: return await self._repository.list_messages(campaign_id)
    async def _context(self,campaign_id:UUID,recipient_id:UUID)->tuple[Campaign,CampaignRecipient,OutreachCandidate]:
        campaign=await self._require_campaign(campaign_id); recipient=await self._repository.get_recipient(recipient_id)
        if recipient is None or recipient.campaign_id != campaign_id: raise OutreachError("Campaign recipient was not found.")
        candidate=await self._repository.get_candidate(recipient.candidate_id)
        if candidate is None: raise OutreachError("Recipient candidate was not found.")
        return campaign,recipient,candidate
    async def _require_campaign(self, campaign_id:UUID)->Campaign:
        value=await self._repository.get_campaign(campaign_id)
        if value is None: raise OutreachError("Campaign was not found.")
        return value
    async def _require_message(self,message_id:UUID)->OutreachMessage:
        value=await self._repository.get_message(message_id)
        if value is None: raise OutreachError("Outreach message was not found.")
        return value
    def _render(self, template:str,candidate:OutreachCandidate)->str:
        values={"contact_name":candidate.contact_name or "there","company_name":candidate.domain,"domain":candidate.domain,"website_url":str(candidate.website_url),"target_url":"","opportunity_type":""}
        missing={name for name in self._VARIABLE.findall(template) if name not in values}
        if missing: raise OutreachError(f"Template has unsupported variables: {', '.join(sorted(missing))}.")
        return self._VARIABLE.sub(lambda match: values[match.group(1)],template).strip()
