"""Gmail OAuth, safe sending, and narrowly scoped reply retrieval providers."""
from __future__ import annotations
import asyncio,base64
from collections.abc import Awaitable,Callable,Sequence
from email.message import EmailMessage
from email.utils import parseaddr,parsedate_to_datetime
from typing import Any
import httpx
from src.core.constants import DEFAULT_RETRY_COUNT,DEFAULT_RETRY_DELAY_SECONDS,SEARCH_TIMEOUT_SECONDS
from src.core.exceptions import OutreachError
from src.outreach.domain.crm import OutreachReply,ReplyClassification
from src.outreach.domain.models import OutreachMessage
from src.outreach.providers.delivery import DeliveryResult,EmailSendProvider

class GmailProviderError(OutreachError):pass
class GmailAuthenticationError(GmailProviderError):pass
class GmailPermissionError(GmailProviderError):pass
class GmailSendOutcomeUnknown(GmailProviderError):pass

class GmailOAuthClient:
 token_uri="https://oauth2.googleapis.com/token"
 def __init__(self,client_id:str,client_secret:str,refresh_token:str,*,token_uri:str|None=None,client:httpx.AsyncClient|None=None,client_factory=httpx.AsyncClient,sleep:Callable[[float],Awaitable[None]]=asyncio.sleep):
  if not all(x.strip() for x in (client_id,client_secret,refresh_token)):raise GmailAuthenticationError("Gmail OAuth requires GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, and GMAIL_REFRESH_TOKEN.")
  self._client_id=client_id.strip();self._client_secret=client_secret.strip();self._refresh_token=refresh_token.strip();self.token_uri=(token_uri or self.token_uri).strip();self._client=client;self._factory=client_factory;self._owns=client is None;self._access_token:str|None=None;self._sleep=sleep
 async def token(self)->str:
  if self._access_token:return self._access_token
  client=await self.client();last_error=None
  for attempt in range(DEFAULT_RETRY_COUNT):
   try:response=await client.post(self.token_uri,data={"client_id":self._client_id,"client_secret":self._client_secret,"refresh_token":self._refresh_token,"grant_type":"refresh_token"})
   except (httpx.TimeoutException,httpx.TransportError) as exc:
    last_error=exc
    if attempt+1<DEFAULT_RETRY_COUNT:await self._sleep(DEFAULT_RETRY_DELAY_SECONDS*(attempt+1));continue
    raise GmailAuthenticationError("Gmail OAuth token exchange failed after bounded retries.") from exc
   if response.status_code in {429,500,502,503,504} and attempt+1<DEFAULT_RETRY_COUNT:await self._sleep(DEFAULT_RETRY_DELAY_SECONDS*(attempt+1));continue
   break
  if response.status_code==401:raise GmailAuthenticationError("Gmail OAuth credentials were rejected.")
  if response.status_code==403:raise GmailPermissionError("Gmail OAuth permission was denied.")
  if response.status_code>=400:
   try:reason=str(response.json().get("error") or "")
   except Exception:reason=""
   if reason=="invalid_grant":raise GmailAuthenticationError("Gmail refresh token is invalid, expired, or revoked.")
   raise GmailAuthenticationError("Gmail OAuth token exchange failed.")
  try:value=response.json()["access_token"]
  except (KeyError,TypeError,ValueError) as exc:raise GmailAuthenticationError("Gmail OAuth response did not contain an access token.") from exc
  self._access_token=str(value);return self._access_token
 async def client(self):
  if self._client is None:self._client=self._factory(timeout=SEARCH_TIMEOUT_SECONDS)
  return self._client
 async def aclose(self):
  if self._owns and self._client is not None:await self._client.aclose();self._client=None

class GmailEmailSendProvider(EmailSendProvider):
 provider_name="GMAIL";base_url="https://gmail.googleapis.com/gmail/v1"
 def __init__(self,oauth:GmailOAuthClient,sender_email:str,*,live_enabled:bool=False,sleep:Callable[[float],Awaitable[None]]=asyncio.sleep):
  if not sender_email.strip():raise GmailProviderError("GMAIL_SENDER_EMAIL is required for Gmail sending.")
  self._oauth=oauth;self.sender_email=sender_email.strip();self.live_enabled=live_enabled;self._sleep=sleep
 @staticmethod
 def encode_message(sender:str,recipient:str,subject:str,body:str,*,reply_to:str|None=None,in_reply_to:str|None=None,references:str|None=None)->str:
  message=EmailMessage();message["From"]=sender;message["To"]=recipient;message["Subject"]=subject
  if reply_to:message["Reply-To"]=reply_to
  if in_reply_to:message["In-Reply-To"]=in_reply_to
  if references:message["References"]=references
  message.set_content(body);return base64.urlsafe_b64encode(message.as_bytes()).decode("ascii").rstrip("=")
 async def send(self,*,recipient:str,subject:str,body:str,idempotency_key:str)->DeliveryResult:
  del idempotency_key
  if not self.live_enabled:raise GmailProviderError("Gmail live sending is disabled by GMAIL_LIVE_SEND_ENABLED.")
  if not parseaddr(recipient)[1] or "@" not in parseaddr(recipient)[1]:return DeliveryResult(False,error_code="invalid_recipient",error_message="Recipient address is invalid.")
  raw=self.encode_message(self.sender_email,recipient,subject,body);token=await self._oauth.token();client=await self._oauth.client();url=f"{self.base_url}/users/me/messages/send"
  for attempt in range(DEFAULT_RETRY_COUNT):
   try:response=await client.post(url,json={"raw":raw},headers={"Authorization":f"Bearer {token}"})
   except (httpx.TimeoutException,httpx.TransportError) as exc:raise GmailSendOutcomeUnknown("Gmail send outcome is unknown; reconcile before retrying.") from exc
   if response.status_code in {400,401,403}:return DeliveryResult(False,error_code=str(response.status_code),error_message="Gmail rejected the send request.")
   if response.status_code in {429,500,502,503,504}:
    if attempt+1<DEFAULT_RETRY_COUNT:await self._sleep(DEFAULT_RETRY_DELAY_SECONDS*(attempt+1));continue
    return DeliveryResult(False,error_code=str(response.status_code),error_message="Gmail transient send failure.",rate_limited=response.status_code==429)
   try:response.raise_for_status();data=response.json()
   except (httpx.HTTPError,ValueError) as exc:raise GmailProviderError("Gmail returned an invalid send response.") from exc
   return DeliveryResult(True,provider_message_id=str(data.get("id") or ""),thread_id=str(data.get("threadId") or "") or None,label_ids=tuple(data.get("labelIds") or ()))
  return DeliveryResult(False,error_code="provider_error")
 async def aclose(self):await self._oauth.aclose()

class GmailReplyProvider:
 provider_name="GMAIL";base_url="https://gmail.googleapis.com/gmail/v1"
 def __init__(self,oauth:GmailOAuthClient,sender_email:str):self._oauth=oauth;self.sender_email=sender_email.casefold()
 async def replies(self,tracked_messages:Sequence[OutreachMessage]=())->Sequence[OutreachReply]:
  token=await self._oauth.token();client=await self._oauth.client();output=[];seen=set()
  for tracked in tracked_messages:
   thread_id=tracked.provider_thread_id
   if not thread_id or thread_id in seen:continue
   seen.add(thread_id);response=await client.get(f"{self.base_url}/users/me/threads/{thread_id}",params={"format":"metadata","metadataHeaders":["From","To","Subject","Message-ID","Date"]},headers={"Authorization":f"Bearer {token}"})
   if response.status_code==401:raise GmailAuthenticationError("Gmail reply access was rejected.")
   if response.status_code==403:raise GmailPermissionError("Gmail readonly permission is missing.")
   try:response.raise_for_status();messages=response.json().get("messages") or []
   except (httpx.HTTPError,ValueError) as exc:raise GmailProviderError("Gmail thread retrieval failed.") from exc
   for item in messages:
    if str(item.get("id"))==tracked.provider_message_id:continue
    headers={x.get("name","").casefold():x.get("value","") for x in item.get("payload",{}).get("headers",[])};sender=parseaddr(headers.get("from",""))[1].casefold()
    if not sender or sender==self.sender_email:continue
    snippet=str(item.get("snippet") or "")[:1000];classification=self.classify(headers.get("subject","")+" "+snippet)
    try:received_at=parsedate_to_datetime(headers.get("date","") or "")
    except (TypeError,ValueError):received_at=None
    reply=OutreachReply(message_id=tracked.message_id,provider_message_id=str(item.get("id") or ""),provider_thread_id=thread_id,provider=self.provider_name,sender=sender,recipient=parseaddr(headers.get("to",""))[1],subject=headers.get("subject","")[:300],snippet=snippet,classification=classification)
    if received_at is not None:reply=reply.model_copy(update={"received_at":received_at})
    output.append(reply)
  return tuple(output)
 @staticmethod
 def classify(text:str)->ReplyClassification:
  value=text.casefold()
  if any(x in value for x in ("unsubscribe","remove me","do not contact")):return ReplyClassification.UNSUBSCRIBE
  if any(x in value for x in ("automatic reply","out of office","auto-reply")):return ReplyClassification.AUTO_REPLY
  if "?" in value:return ReplyClassification.QUESTION
  if any(x in value for x in ("interested","sounds good","yes,","happy to")):return ReplyClassification.POSITIVE
  if any(x in value for x in ("not interested","no thanks","decline")):return ReplyClassification.NEGATIVE
  return ReplyClassification.UNKNOWN
 async def aclose(self):await self._oauth.aclose()
