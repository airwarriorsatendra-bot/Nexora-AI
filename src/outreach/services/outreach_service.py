"""Campaign, template, safety, and explicit-delivery orchestration."""

from __future__ import annotations

import logging
import re
import asyncio
from datetime import timedelta
from urllib.parse import urlparse
from uuid import UUID

from src.core.enums import CampaignStatus, DeliveryAttemptStatus, MessageStatus, RecipientStatus, SuppressionReason
from src.core.exceptions import OutreachError, RepositoryError
from src.outreach.domain.models import Campaign, CampaignRecipient, OutreachCandidate, OutreachMessage, utc_now
from src.outreach.dto.requests import AddCandidateRequest, AddRecipientRequest, CreateCampaignRequest, PrepareMessageRequest, SendMessageRequest
from src.outreach.providers.delivery import OutreachDeliveryProvider
from src.outreach.repositories.outreach_repository import OutreachAutomationRepository
from src.outreach.domain.crm import CampaignAnalytics,CRMState,OutreachContact,OutreachHistoryEvent,OutreachProspect,OutreachReply,OutreachSequence,ReplyClassification,SequenceStep,VerificationState
from src.outreach.providers.contracts import ContactDiscoveryProvider,EmailVerificationProvider,ReplyProvider
from src.outreach.providers.gmail import GmailSendOutcomeUnknown


class OutreachService:
    """Safe workflow: create/prepare/validate/explicit-send, with no hidden delivery."""

    _VARIABLE = re.compile(r"{{\s*([a-z_]+)\s*}}")
    _TRANSITIONS = {
        CampaignStatus.DRAFT: {CampaignStatus.READY, CampaignStatus.CANCELLED},
        CampaignStatus.READY: {CampaignStatus.ACTIVE, CampaignStatus.PAUSED, CampaignStatus.CANCELLED},
        CampaignStatus.ACTIVE: {CampaignStatus.PAUSED, CampaignStatus.COMPLETED, CampaignStatus.CANCELLED},
        CampaignStatus.PAUSED: {CampaignStatus.ACTIVE, CampaignStatus.CANCELLED},
        CampaignStatus.COMPLETED: {CampaignStatus.ARCHIVED}, CampaignStatus.CANCELLED: {CampaignStatus.ARCHIVED},CampaignStatus.ARCHIVED:set(),
    }

    _CRM_TRANSITIONS={
        CRMState.NEW:{CRMState.RESEARCHING,CRMState.CONTACT_FOUND,CRMState.ARCHIVED},CRMState.RESEARCHING:{CRMState.CONTACT_FOUND,CRMState.DO_NOT_CONTACT,CRMState.ARCHIVED},CRMState.CONTACT_FOUND:{CRMState.READY_FOR_OUTREACH,CRMState.DO_NOT_CONTACT},CRMState.READY_FOR_OUTREACH:{CRMState.IN_CAMPAIGN,CRMState.DO_NOT_CONTACT},CRMState.IN_CAMPAIGN:{CRMState.CONTACTED,CRMState.DO_NOT_CONTACT},CRMState.CONTACTED:{CRMState.FOLLOW_UP_DUE,CRMState.REPLIED,CRMState.NO_RESPONSE,CRMState.BOUNCED},CRMState.FOLLOW_UP_DUE:{CRMState.CONTACTED,CRMState.REPLIED,CRMState.NO_RESPONSE},CRMState.REPLIED:{CRMState.POSITIVE_REPLY,CRMState.NEGATIVE_REPLY,CRMState.WON,CRMState.LOST},CRMState.POSITIVE_REPLY:{CRMState.WON,CRMState.LOST},CRMState.NEGATIVE_REPLY:{CRMState.LOST},CRMState.NO_RESPONSE:{CRMState.ARCHIVED},CRMState.BOUNCED:{CRMState.DO_NOT_CONTACT},CRMState.UNSUBSCRIBED:{CRMState.DO_NOT_CONTACT},CRMState.DO_NOT_CONTACT:{CRMState.ARCHIVED},CRMState.WON:{CRMState.ARCHIVED},CRMState.LOST:{CRMState.ARCHIVED},CRMState.ARCHIVED:set(),
    }

    def __init__(self, repository: OutreachAutomationRepository, delivery_provider: OutreachDeliveryProvider, logger: logging.Logger | None = None, *, contact_provider:ContactDiscoveryProvider|None=None,verification_provider:EmailVerificationProvider|None=None,reply_provider:ReplyProvider|None=None,max_emails_per_run:int=10,max_emails_per_day:int=50,sleep=asyncio.sleep) -> None:
        self._repository, self._delivery = repository, delivery_provider
        self._contact_provider,self._verification_provider,self._reply_provider=contact_provider,verification_provider,reply_provider
        self.max_emails_per_run=max(1,max_emails_per_run);self.max_emails_per_day=max(1,max_emails_per_day)
        self._sleep=sleep
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
            await self._repository.save_message(message.model_copy(update={"status":MessageStatus.SUPPRESSED,"error_state":"suppressed"}))
            raise OutreachError("Recipient is suppressed and cannot receive outreach.")
        if message.sequence_step > 1 and recipient.status is not RecipientStatus.SENT: raise OutreachError("Follow-up requires a successful prior contact.")
        if await self._repository.sent_attempt_exists(message.message_id): return message.model_copy(update={"status": MessageStatus.SENT})
        if request.dry_run:
            await self._repository.save_attempt(message.message_id, self._delivery.provider_name, DeliveryAttemptStatus.SIMULATED.value)
            return await self._repository.save_message(message.model_copy(update={"status": MessageStatus.DRY_RUN}))
        result=None;last_error=None
        for attempt in range(3):
            try:
                result=await self._delivery.send(recipient=str(candidate.email), subject=message.subject, body=message.body, idempotency_key=f"{message.campaign_id}:{message.recipient_id}:{message.sequence_step}")
                transient=result.rate_limited or str(result.error_code or "").lower() in {"429","500","502","503","504","timeout","network"}
                if result.accepted or not transient:break
            except GmailSendOutcomeUnknown as exc:
                await self._repository.save_attempt(message.message_id,self._delivery.provider_name,"send_outcome_unknown",error_code="uncertain",error_message="Provider outcome requires reconciliation.")
                return await self._repository.save_message(message.model_copy(update={"status":MessageStatus.SEND_OUTCOME_UNKNOWN,"provider":self._delivery.provider_name,"error_state":"uncertain"}))
            except (TimeoutError,OSError) as exc:last_error=exc
            if attempt<2:await self._sleep(attempt+1)
        if result is None:
            await self._repository.save_attempt(message.message_id,self._delivery.provider_name,DeliveryAttemptStatus.FAILED.value,error_code="transport",error_message="Transient delivery failure.")
            return await self._repository.save_message(message.model_copy(update={"status":MessageStatus.FAILED}))
        if result.accepted:
            sent = message.model_copy(update={"status": MessageStatus.SENT, "sent_at": utc_now(), "provider_message_id": result.provider_message_id,"provider_thread_id":result.thread_id,"provider":self._delivery.provider_name})
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
        values={"contact_name":candidate.contact_name or "there","first_name":(candidate.contact_name.split()[0] if candidate.contact_name else "there"),"company_name":candidate.domain,"domain":candidate.domain,"website_url":str(candidate.website_url),"target_url":"","target_page":"","relevant_page":"","opportunity_type":"","evidence_reason":""}
        missing={name for name in self._VARIABLE.findall(template) if name not in values}
        if missing: raise OutreachError(f"Template has unsupported variables: {', '.join(sorted(missing))}.")
        return self._VARIABLE.sub(lambda match: values[match.group(1)],template).strip()

    async def import_handoff(self,handoff)->OutreachProspect:
        value=OutreachProspect(prospect_id=handoff.prospect_id,domain=handoff.domain,representative_url=handoff.representative_url,target_page=handoff.target_page,opportunity_type=handoff.opportunity_type.value,risk=handoff.risk,relevance=handoff.relevance,score=handoff.score,priority=handoff.priority.value,contactability=handoff.contactability,discovery_source=handoff.discovery_source,evidence_summary=handoff.evidence_summary,moz_domain_authority=handoff.authority_evidence.domain_authority if handoff.authority_evidence else None,moz_page_authority=handoff.authority_evidence.page_authority if handoff.authority_evidence else None,moz_spam_score=handoff.authority_evidence.spam_score if handoff.authority_evidence else None)
        await self._repository.save_prospect(value);await self._event("prospect",value.prospect_id,"imported","Beta 14 evidence preserved without recalculation.");return value
    async def transition_prospect(self,prospect:OutreachProspect,target:CRMState)->OutreachProspect:
        if target not in self._CRM_TRANSITIONS[prospect.state]:raise OutreachError(f"Prospect cannot transition from {prospect.state.value} to {target.value}.")
        changed=prospect.model_copy(update={"state":target,"last_action_at":utc_now()});await self._repository.save_prospect(changed);await self._event("prospect",changed.prospect_id,"state_changed",f"{prospect.state.value}->{target.value}");return changed
    async def add_contact(self,contact:OutreachContact)->OutreachContact:
        value=await self._repository.save_contact(contact);await self._event("contact",value.contact_id,"contact_saved",value.source);return value
    async def discover_contacts(self,prospect:OutreachProspect)->tuple[OutreachContact,...]:
        if self._contact_provider is None:return ()
        values=tuple(await self._contact_provider.discover(prospect.domain))
        for value in values:await self.add_contact(value.model_copy(update={"prospect_id":prospect.prospect_id}))
        return values
    async def verify_contact(self,contact:OutreachContact)->OutreachContact:
        if self._verification_provider is None:return contact
        state=await self._verification_provider.verify(str(contact.email));changed=contact.model_copy(update={"verification_state":state});await self._repository.save_contact(changed)
        if state is VerificationState.INVALID:await self._repository.suppress(str(contact.email),SuppressionReason.INVALID_ADDRESS)
        return changed
    async def create_sequence(self,name:str,steps:list[SequenceStep])->OutreachSequence:
        sequence=await self._repository.save_sequence(OutreachSequence(name=name))
        for step in steps:
            if step.sequence_id!=sequence.sequence_id:step=step.model_copy(update={"sequence_id":sequence.sequence_id})
            await self._repository.save_sequence_step(step)
        return sequence
    async def record_reply(self,reply:OutreachReply)->OutreachReply:
        value=await self._repository.save_reply(reply);message=await self._require_message(reply.message_id);await self._repository.save_message(message.model_copy(update={"status":MessageStatus.REPLIED}));recipient=await self._repository.get_recipient(message.recipient_id)
        if recipient:await self._repository.save_recipient(recipient.model_copy(update={"status":RecipientStatus.REPLIED,"next_followup_at":None}))
        for pending in await self._repository.list_messages(message.campaign_id):
            if pending.recipient_id==message.recipient_id and pending.sequence_step>message.sequence_step and pending.status in {MessageStatus.PREPARED,MessageStatus.QUEUED}:await self._repository.save_message(pending.model_copy(update={"status":MessageStatus.CANCELLED,"error_state":"reply_received"}))
        if reply.classification is ReplyClassification.UNSUBSCRIBE and recipient:
            candidate=await self._repository.get_candidate(recipient.candidate_id)
            if candidate:await self._repository.suppress(str(candidate.email),SuppressionReason.UNSUBSCRIBE)
        await self._event("message",message.message_id,"reply_received",reply.classification.value);return value
    async def sync_replies(self)->tuple[OutreachReply,...]:
        if self._reply_provider is None:return ()
        values=tuple(await self._reply_provider.replies(await self._repository.list_all_messages()))
        persisted=await self._repository.list_replies()
        known_provider_ids={value.provider_message_id for value in persisted if value.provider_message_id}
        known_message_ids={value.message_id for value in persisted}
        new_values=tuple(value for value in values if (value.provider_message_id and value.provider_message_id not in known_provider_ids) or (not value.provider_message_id and value.message_id not in known_message_ids))
        for value in new_values:await self.record_reply(value)
        return new_values
    async def analytics(self)->CampaignAnalytics:
        prospects=await self._repository.list_prospects();contacts=await self._repository.list_contacts();messages=await self._repository.list_all_messages();replies=await self._repository.list_replies();return CampaignAnalytics(prospects=len(prospects),contacts=len(contacts),sent=sum(x.status in {MessageStatus.SENT,MessageStatus.REPLIED,MessageStatus.BOUNCED} for x in messages),failed=sum(x.status is MessageStatus.FAILED for x in messages),bounced=sum(x.status is MessageStatus.BOUNCED for x in messages),replies=len(replies),positive_replies=sum(x.classification is ReplyClassification.POSITIVE for x in replies),negative_replies=sum(x.classification is ReplyClassification.NEGATIVE for x in replies))
    async def snapshot(self)->dict[str,object]:
        prospects=await self._repository.list_prospects();contacts=await self._repository.list_contacts();campaigns=await self._repository.list_campaigns();sequences=await self._repository.list_sequences();steps=await self._repository.list_sequence_steps();messages=await self._repository.list_all_messages();replies=await self._repository.list_replies();suppressions=await self._repository.list_suppressions();history=await self._repository.list_history();analytics=await self.analytics();followups=[x for x in messages if x.scheduled_at and x.status in {MessageStatus.PREPARED,MessageStatus.QUEUED}];provider_name=self._delivery.provider_name;gmail_configured=provider_name=="GMAIL";live_send_enabled=bool(getattr(self._delivery,"live_enabled",False));sender_email=str(getattr(self._delivery,"sender_email","") or "");reply_provider_configured=self._reply_provider is not None;return locals()
    async def _event(self,entity_type:str,entity_id:UUID,event_type:str,detail:str="")->None:await self._repository.save_history(OutreachHistoryEvent(entity_type=entity_type,entity_id=entity_id,event_type=event_type,detail=detail))
