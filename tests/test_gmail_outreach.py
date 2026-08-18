"""Offline Gmail OAuth, send, MIME, thread, and isolation tests."""
from __future__ import annotations
import base64,email,tempfile,unittest
from pathlib import Path
from uuid import uuid4
import httpx
from src.core.enums import MessageStatus
from src.outreach.composition import OutreachComposition,OutreachSettings
from src.outreach.domain.models import OutreachMessage
from src.outreach.providers.gmail import GmailAuthenticationError,GmailEmailSendProvider,GmailOAuthClient,GmailPermissionError,GmailReplyProvider,GmailSendOutcomeUnknown
from src.outreach.providers.contracts import FakeReplyProvider
from src.outreach.providers.delivery import FakeDeliveryProvider
from src.outreach.services.outreach_service import OutreachService

class RouteTransport(httpx.AsyncBaseTransport):
 def __init__(self,outcomes):self.outcomes=list(outcomes);self.requests=[]
 async def handle_async_request(self,request):
  self.requests.append(request);value=self.outcomes.pop(0)
  if isinstance(value,Exception):raise value
  status,payload=value;return httpx.Response(status,json=payload,request=request)

class GmailOutreachTests(unittest.IsolatedAsyncioTestCase):
 async def oauth(self,outcomes):
  transport=RouteTransport(outcomes);client=httpx.AsyncClient(transport=transport);oauth=GmailOAuthClient("gmail-client","gmail-secret","gmail-refresh",client=client,sleep=lambda _:self.noop());return oauth,transport,client
 async def test_token_exchange_success_invalid_grant_401_403_and_secret_safety(self):
  oauth,transport,client=await self.oauth([(200,{"access_token":"access"})]);self.assertEqual(await oauth.token(),"access");self.assertIn(b"grant_type=refresh_token",transport.requests[0].content);await client.aclose()
  for status,payload,error in ((400,{"error":"invalid_grant"},GmailAuthenticationError),(401,{},GmailAuthenticationError),(403,{},GmailPermissionError)):
   oauth,_,client=await self.oauth([(status,payload)])
   with self.assertRaises(error) as raised:await oauth.token()
   self.assertNotIn("gmail-secret",str(raised.exception));self.assertNotIn("gmail-refresh",str(raised.exception));await client.aclose()
  oauth,transport,client=await self.oauth([(429,{}),(500,{}),(200,{"access_token":"retried"})]);self.assertEqual(await oauth.token(),"retried");self.assertEqual(len(transport.requests),3);await client.aclose()
 async def test_mime_base64_send_ids_and_live_flag(self):
  oauth,transport,client=await self.oauth([(200,{"access_token":"access"}),(200,{"id":"m1","threadId":"t1","labelIds":["SENT"]})]);provider=GmailEmailSendProvider(oauth,"sender@example.com",live_enabled=True,sleep=lambda _:self.noop());result=await provider.send(recipient="recipient@example.com",subject="Hello",body="Plain text",idempotency_key="one");self.assertTrue(result.accepted);self.assertEqual(result.thread_id,"t1")
  payload=transport.requests[1].content.decode();import json;raw=json.loads(payload)["raw"];decoded=base64.urlsafe_b64decode(raw+"="*(-len(raw)%4));message=email.message_from_bytes(decoded);self.assertEqual(message["From"],"sender@example.com");self.assertEqual(message["To"],"recipient@example.com");await client.aclose()
  oauth,_,client=await self.oauth([]);disabled=GmailEmailSendProvider(oauth,"sender@example.com",live_enabled=False)
  with self.assertRaises(Exception):await disabled.send(recipient="recipient@example.com",subject="x",body="y",idempotency_key="x")
  await client.aclose()
 async def noop(self):return None
 async def test_send_status_retry_and_uncertain_timeout(self):
  for status in (400,401,403):
   oauth,transport,client=await self.oauth([(200,{"access_token":"a"}),(status,{})]);result=await GmailEmailSendProvider(oauth,"s@example.com",live_enabled=True).send(recipient="r@example.com",subject="s",body="b",idempotency_key="i");self.assertFalse(result.accepted);self.assertEqual(len(transport.requests),2);await client.aclose()
  oauth,transport,client=await self.oauth([(200,{"access_token":"a"}),(429,{}),(500,{}),(200,{"id":"m","threadId":"t"})]);result=await GmailEmailSendProvider(oauth,"s@example.com",live_enabled=True,sleep=lambda _:self.noop()).send(recipient="r@example.com",subject="s",body="b",idempotency_key="i");self.assertTrue(result.accepted);self.assertEqual(len(transport.requests),4);await client.aclose()
  request=httpx.Request("POST","https://gmail.googleapis.com");oauth,_,client=await self.oauth([(200,{"access_token":"a"}),httpx.ReadTimeout("uncertain",request=request)])
  with self.assertRaises(GmailSendOutcomeUnknown) as raised:await GmailEmailSendProvider(oauth,"s@example.com",live_enabled=True).send(recipient="r@example.com",subject="s",body="b",idempotency_key="i")
  self.assertIsNotNone(raised.exception.__cause__);await client.aclose()
 async def test_thread_reply_detection_excludes_outbound_and_classifies(self):
  thread={"messages":[{"id":"out","payload":{"headers":[{"name":"From","value":"sender@example.com"}]}},{"id":"in","snippet":"Yes, interested","payload":{"headers":[{"name":"From","value":"Person <reply@example.com>"},{"name":"To","value":"sender@example.com"},{"name":"Subject","value":"Re: hello"},{"name":"Date","value":"Tue, 18 Aug 2026 16:45:00 +0000"}]}}]};oauth,_,client=await self.oauth([(200,{"access_token":"a"}),(200,thread)]);provider=GmailReplyProvider(oauth,"sender@example.com");tracked=OutreachMessage(campaign_id=uuid4(),recipient_id=uuid4(),subject="Hello",body="Body",status=MessageStatus.SENT,provider_message_id="out",provider_thread_id="thread");replies=await provider.replies([tracked]);self.assertEqual(len(replies),1);self.assertEqual(replies[0].classification.value,"positive");self.assertEqual(replies[0].provider,"GMAIL");self.assertEqual(replies[0].received_at.year,2026);await client.aclose()
 async def test_reply_sync_returns_only_new_provider_observations(self):
  tracked=OutreachMessage(campaign_id=uuid4(),recipient_id=uuid4(),subject="Hello",body="Body",status=MessageStatus.SENT,provider_message_id="out",provider_thread_id="thread")
  from src.outreach.domain.crm import OutreachReply
  reply=OutreachReply(message_id=tracked.message_id,provider_message_id="in",provider_thread_id="thread",provider="GMAIL")
  class Repository:
   def __init__(self):self.replies=[]
   async def list_all_messages(self):return [tracked]
   async def list_replies(self):return list(self.replies)
  repository=Repository();provider=FakeReplyProvider([reply]);service=OutreachService(repository,FakeDeliveryProvider(),reply_provider=provider)
  async def record(value):repository.replies.append(value);return value
  service.record_reply=record
  self.assertEqual(await service.sync_replies(),(reply,));self.assertEqual(await service.sync_replies(),())
 async def test_configuration_uses_only_gmail_credentials_and_lifecycle(self):
  environment={"GSC_CLIENT_ID":"gsc","GSC_CLIENT_SECRET":"gsc-secret","GSC_REFRESH_TOKEN":"gsc-refresh"};settings=OutreachSettings.from_environment(environment);self.assertFalse(settings.gmail_configured)
  environment.update({"GMAIL_CLIENT_ID":"gmail","GMAIL_CLIENT_SECRET":"secret","GMAIL_REFRESH_TOKEN":"refresh","GMAIL_SENDER_EMAIL":"sender@example.com","GMAIL_LIVE_SEND_ENABLED":"false"});settings=OutreachSettings.from_environment(environment);self.assertTrue(settings.gmail_configured);app=OutreachComposition(settings).build();self.assertEqual(app.service._delivery.provider_name,"GMAIL");self.assertFalse(app.service._delivery.live_enabled);await app.aclose()
