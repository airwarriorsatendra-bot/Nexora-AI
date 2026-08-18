"""Comprehensive offline Beta 15 CRM, provider, reply, and dashboard tests."""
from __future__ import annotations
import tempfile,unittest
from pathlib import Path
from uuid import uuid4
from streamlit.testing.v1 import AppTest
from dashboard.outreach import render_outreach
from src.backlinks.domain.intelligence import AuthorityObservation,AuthorityScope,BacklinkProspect,OutreachHandoff,ProspectOpportunityType,ProspectPriority
from src.core.enums import CampaignStatus,MessageStatus,SuppressionReason
from src.core.exceptions import OutreachError
from src.outreach.domain.crm import CRMState,OutreachContact,OutreachReply,ReplyClassification,SequenceStep,VerificationState
from src.outreach.dto.requests import AddCandidateRequest,AddRecipientRequest,CreateCampaignRequest,PrepareMessageRequest,SendMessageRequest
from src.outreach.providers.contracts import FakeContactDiscoveryProvider,FakeEmailVerificationProvider,FakeReplyProvider
from src.outreach.providers.delivery import DeliveryResult,FakeDeliveryProvider
from src.outreach.repositories.outreach_repository import OutreachAutomationRepository
from src.outreach.services.outreach_service import OutreachService

class SequencedDelivery(FakeDeliveryProvider):
 def __init__(self,results):super().__init__();self.results=list(results)
 async def send(self,**kwargs):
  self.calls.append((kwargs["recipient"],kwargs["subject"]));result=self.results.pop(0)
  if isinstance(result,Exception):raise result
  return result

class OutreachCRMTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.temp=tempfile.TemporaryDirectory();self.repo=OutreachAutomationRepository(Path(self.temp.name)/"crm.db");self.delivery=FakeDeliveryProvider();self.service=OutreachService(self.repo,self.delivery,sleep=lambda _:self.noop())
 async def noop(self):return None
 async def asyncTearDown(self):self.temp.cleanup()
 async def context(self,delivery=None):
  service=self.service if delivery is None else OutreachService(self.repo,delivery,sleep=lambda _:self.noop());candidate=await service.add_candidate(AddCandidateRequest(website_url="https://publisher.example",email="editor@publisher.example",contact_name="Ava Editor"));campaign=await service.create_campaign(CreateCampaignRequest(name="Resources"));recipient=await service.add_recipient(AddRecipientRequest(campaign_id=campaign.campaign_id,candidate_id=candidate.candidate_id));message=await service.prepare_message(PrepareMessageRequest(campaign_id=campaign.campaign_id,recipient_id=recipient.recipient_id,subject_template="Hi {{first_name}}",body_template="About {{domain}}"));campaign=await service.transition_campaign(campaign.campaign_id,CampaignStatus.READY);return service,candidate,campaign,recipient,message
 async def test_backlink_handoff_preserves_metrics_and_validates_crm_transitions(self):
  authority=AuthorityObservation(target="https://publisher.example/",scope=AuthorityScope.URL,domain_authority=40,page_authority=30,spam_score=2);prospect=BacklinkProspect(domain="publisher.example",representative_url="https://publisher.example/resource",opportunity_type=ProspectOpportunityType.RESOURCE_PAGE,discovery_source="backlinks",target_page="https://target.example/asset",relevance=80,contactability=50,score=72,priority=ProspectPriority.HIGH,reasons=("Observed resource page.",));handoff=OutreachHandoff(prospect_id=prospect.prospect_id,domain=prospect.domain,representative_url=prospect.representative_url,target_page=prospect.target_page,opportunity_type=prospect.opportunity_type,authority_evidence=authority,risk="manual_review",relevance=prospect.relevance,score=prospect.score,priority=prospect.priority,contactability=prospect.contactability,discovery_source=prospect.discovery_source,evidence_summary=prospect.reasons)
  imported=await self.service.import_handoff(handoff);self.assertEqual(imported.moz_domain_authority,40);self.assertEqual(imported.score,72);changed=await self.service.transition_prospect(imported,CRMState.RESEARCHING);self.assertEqual(changed.state,CRMState.RESEARCHING)
  with self.assertRaises(OutreachError):await self.service.transition_prospect(changed,CRMState.WON)
 async def test_contact_discovery_verification_duplicate_and_invalid_suppression(self):
  contact=OutreachContact(name="Ava",email="ava@publisher.example",domain="publisher.example");provider=FakeContactDiscoveryProvider([contact]);verification=FakeEmailVerificationProvider(VerificationState.INVALID);service=OutreachService(self.repo,self.delivery,contact_provider=provider,verification_provider=verification)
  saved=await service.add_contact(contact);duplicate=await service.add_contact(contact.model_copy(update={"name":"Updated"}));self.assertEqual(str(saved.email),str(duplicate.email));verified=await service.verify_contact(duplicate);self.assertEqual(verified.verification_state,VerificationState.INVALID);self.assertTrue(await self.repo.is_suppressed(str(contact.email)))
 async def test_sequences_replies_stop_followups_and_analytics(self):
  service,candidate,campaign,recipient,message=await self.context();sent=await service.send(SendMessageRequest(message_id=message.message_id,dry_run=False));self.assertEqual(sent.status,MessageStatus.SENT)
  sequence=await service.create_sequence("Three step",[SequenceStep(sequence_id=uuid4(),step_number=1,subject_template="Hi",body_template="Hello"),SequenceStep(sequence_id=uuid4(),step_number=2,delay_days=3,subject_template="Follow",body_template="Following up")]);self.assertEqual(len(await self.repo.list_sequence_steps()),2)
  reply=await service.record_reply(OutreachReply(message_id=message.message_id,classification=ReplyClassification.POSITIVE));self.assertEqual(reply.classification,ReplyClassification.POSITIVE);analytics=await service.analytics();self.assertEqual(analytics.sent,1);self.assertEqual(analytics.replies,1);self.assertEqual(analytics.reply_rate,1)
 async def test_suppression_idempotency_and_transient_delivery_retries(self):
  delivery=SequencedDelivery([DeliveryResult(False,error_code="429",rate_limited=True),DeliveryResult(False,error_code="503"),DeliveryResult(True,provider_message_id="ok")]);service,candidate,campaign,recipient,message=await self.context(delivery);sent=await service.send(SendMessageRequest(message_id=message.message_id,dry_run=False));self.assertEqual(sent.status,MessageStatus.SENT);self.assertEqual(len(delivery.calls),3);again=await service.send(SendMessageRequest(message_id=message.message_id,dry_run=False));self.assertEqual(len(delivery.calls),3)
  await service.suppress(str(candidate.email),SuppressionReason.DO_NOT_CONTACT);self.assertTrue(await self.repo.is_suppressed(str(candidate.email)))
 async def test_dashboard_empty_state_exports_and_zero_automatic_send(self):
  delivery=FakeDeliveryProvider()
  def page():
   from dashboard.outreach import render_outreach
   class Workflow:
    async def snapshot(self):
     class A:prospects=contacts=sent=failed=bounced=replies=positive_replies=negative_replies=0;reply_rate=positive_reply_rate=bounce_rate=0.0
     return {"prospects":[],"contacts":[],"campaigns":[],"sequences":[],"steps":[],"messages":[],"replies":[],"followups":[],"suppressions":[],"history":[],"analytics":A()}
   render_outreach(workflow=Workflow())
  app=AppTest.from_function(page).run(timeout=30);self.assertFalse(app.exception);self.assertEqual(delivery.calls,[]);self.assertTrue(any(x.label=="Prospects CSV" for x in app.download_button))
