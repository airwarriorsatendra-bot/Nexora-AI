"""Offline tests for campaign safety, persistence, and delivery idempotency."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from dashboard.outreach_workflow import OutreachDashboardWorkflow, messages_to_dataframe
from src.core.enums import CampaignStatus, MessageStatus, RecipientStatus, SuppressionReason
from src.core.exceptions import OutreachError
from src.outreach.composition import OutreachComposition, OutreachSettings
from src.outreach.dto.requests import AddCandidateRequest, AddRecipientRequest, CreateCampaignRequest, PrepareMessageRequest, SendMessageRequest
from src.outreach.providers.delivery import DeliveryResult, FakeDeliveryProvider
from src.outreach.repositories.outreach_repository import OutreachAutomationRepository
from src.outreach.services.outreach_service import OutreachService


class OutreachAutomationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp=tempfile.TemporaryDirectory(); self.repo=OutreachAutomationRepository(Path(self.temp.name)/"outreach.db"); self.provider=FakeDeliveryProvider(); self.service=OutreachService(self.repo,self.provider)
        self.candidate=await self.service.add_candidate(AddCandidateRequest(website_url="https://publisher.example",email="Editor@Publisher.Example",contact_name="Ava"))
        self.campaign=await self.service.create_campaign(CreateCampaignRequest(name="Guest posts"))

    async def asyncTearDown(self) -> None: self.temp.cleanup()
    async def _message(self, step:int=1):
        recipient=await self.service.add_recipient(AddRecipientRequest(campaign_id=self.campaign.campaign_id,candidate_id=self.candidate.candidate_id))
        return await self.service.prepare_message(PrepareMessageRequest(campaign_id=self.campaign.campaign_id,recipient_id=recipient.recipient_id,subject_template="Hi {{contact_name}}",body_template="Visit {{website_url}}",sequence_step=step))

    async def test_candidate_and_recipient_deduplication_and_template_validation(self) -> None:
        duplicate=await self.service.add_candidate(AddCandidateRequest(website_url="https://other.example",email="editor@publisher.example")); self.assertEqual(duplicate.candidate_id,self.candidate.candidate_id)
        first=await self.service.add_recipient(AddRecipientRequest(campaign_id=self.campaign.campaign_id,candidate_id=self.candidate.candidate_id)); second=await self.service.add_recipient(AddRecipientRequest(campaign_id=self.campaign.campaign_id,candidate_id=self.candidate.candidate_id)); self.assertEqual(first.recipient_id,second.recipient_id)
        with self.assertRaises(OutreachError): await self.service.prepare_message(PrepareMessageRequest(campaign_id=self.campaign.campaign_id,recipient_id=first.recipient_id,subject_template="{{unknown}}",body_template="Hi"))

    async def test_campaign_transitions_dry_run_and_idempotent_fake_delivery(self) -> None:
        message=await self._message(); dry=await self.service.send(SendMessageRequest(message_id=message.message_id,dry_run=True)); self.assertEqual(dry.status,MessageStatus.DRY_RUN); self.assertEqual(self.provider.calls,[])
        with self.assertRaises(OutreachError): await self.service.transition_campaign(self.campaign.campaign_id,CampaignStatus.ACTIVE)
        self.campaign=await self.service.transition_campaign(self.campaign.campaign_id,CampaignStatus.READY); self.campaign=await self.service.transition_campaign(self.campaign.campaign_id,CampaignStatus.ACTIVE)
        sent=await self.service.send(SendMessageRequest(message_id=message.message_id,dry_run=False)); duplicate=await self.service.send(SendMessageRequest(message_id=message.message_id,dry_run=False))
        self.assertEqual(sent.status,MessageStatus.SENT); self.assertEqual(duplicate.status,MessageStatus.SENT); self.assertEqual(len(self.provider.calls),1)

    async def test_suppression_and_followup_reply_block_provider_calls(self) -> None:
        message=await self._message(); self.campaign=await self.service.transition_campaign(self.campaign.campaign_id,CampaignStatus.READY)
        await self.service.suppress(str(self.candidate.email),SuppressionReason.UNSUBSCRIBE)
        with self.assertRaises(OutreachError): await self.service.send(SendMessageRequest(message_id=message.message_id,dry_run=False))
        self.assertEqual(self.provider.calls,[])

        fresh=await self.service.add_candidate(AddCandidateRequest(website_url="https://fresh.example",email="fresh@example.com")); recipient=await self.service.add_recipient(AddRecipientRequest(campaign_id=self.campaign.campaign_id,candidate_id=fresh.candidate_id)); initial=await self.service.prepare_message(PrepareMessageRequest(campaign_id=self.campaign.campaign_id,recipient_id=recipient.recipient_id,subject_template="Hi",body_template="Hello")); await self.service.send(SendMessageRequest(message_id=initial.message_id,dry_run=False)); await self.repo.save_recipient(recipient.model_copy(update={"status":RecipientStatus.REPLIED})); follow=await self.service.prepare_message(PrepareMessageRequest(campaign_id=self.campaign.campaign_id,recipient_id=recipient.recipient_id,subject_template="Follow",body_template="Hello",sequence_step=2))
        with self.assertRaises(OutreachError): await self.service.send(SendMessageRequest(message_id=follow.message_id,dry_run=False))
        self.assertEqual(len(self.provider.calls),1)

    async def test_provider_failure_composition_dashboard_and_export(self) -> None:
        failed=OutreachService(self.repo,FakeDeliveryProvider(DeliveryResult(accepted=False,error_code="timeout",error_message="offline"))); message=await self._message(); self.campaign=await self.service.transition_campaign(self.campaign.campaign_id,CampaignStatus.READY); response=await failed.send(SendMessageRequest(message_id=message.message_id,dry_run=False)); self.assertEqual(response.status,MessageStatus.FAILED)
        provider=FakeDeliveryProvider(); app=OutreachComposition(OutreachSettings(Path(self.temp.name)/"composition.db"),delivery_provider_factory=lambda:provider).build(); await app.aclose()
        workflow=OutreachDashboardWorkflow(application_factory=lambda:OutreachComposition(OutreachSettings(Path(self.temp.name)/"workflow.db")).build()); campaign=await workflow.create_campaign("Workflow","",self.campaign.objective); candidate=await workflow.add_candidate("https://workflow.example","workflow@example.com","W"); message=await workflow.prepare(campaign.campaign_id,candidate.candidate_id,"Hi {{contact_name}}","Hello {{domain}}"); self.assertIn("subject",messages_to_dataframe([message]).columns)
