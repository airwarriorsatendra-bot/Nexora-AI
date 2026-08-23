"""Dedicated HTTP boundary for the existing Outreach CRM service."""
from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Request, status
from api.errors import APIError
from api.schemas.outreach import CampaignCreate,CandidateCreate,MessagePrepare,MessageSendConfirmation,OutreachSnapshotResponse,CampaignResponse,CandidateResponse,PreparedMessageResponse,SentMessageResponse,RepliesResponse,OutreachCollectionResponse,OutreachPage
from api.schemas.pagination import PageMetadata
from src.outreach.composition import OutreachComposition,OutreachSettings
from src.outreach.dto.requests import AddCandidateRequest,AddRecipientRequest,CreateCampaignRequest,PrepareMessageRequest,SendMessageRequest
from src.outreach.repositories.outreach_repository import OutreachAutomationRepository

router=APIRouter(prefix="/outreach",tags=["outreach"])
def response(value):
 if isinstance(value, list): return [item.model_dump(mode="json") if hasattr(item, "model_dump") else item for item in value]
 return value.model_dump(mode="json") if hasattr(value, "model_dump") else value
def app_for(request:Request):
 environment=request.app.state.settings.environment_dict();environment["DATABASE_URL"]=str(request.app.state.settings.database_path);return OutreachComposition(OutreachSettings.from_environment(environment)).build()
async def collection(request: Request, key: str) -> list[dict[str, object]]:
 app=app_for(request)
 try:
  value=await app.service.snapshot()
  return response(value.get(key, []))
 finally: await app.aclose()

async def page_collection(request: Request, key: str, table: str, page: int, limit: int) -> OutreachPage:
 repository = OutreachAutomationRepository(request.app.state.settings.database_path)
 loaders = {"prospects": repository.list_prospects, "contacts": repository.list_contacts, "campaigns": repository.list_campaigns, "sequences": repository.list_sequences, "messages": repository.list_all_messages, "replies": repository.list_replies, "history": repository.list_history, "suppression": repository.list_suppressions}
 values = await loaders[key](max(1, min(10000, page * limit)))
 total = await repository.count_table(table); offset = (page - 1) * limit; items = [value.model_dump(mode="json") if hasattr(value, "model_dump") else value for value in values[offset:offset + limit]]
 return OutreachPage(items=items, pagination=PageMetadata(page=page, limit=limit, returned=len(items), has_more=total > offset + limit))
@router.get("/resources/{resource}", response_model=OutreachPage)
async def resource_page(resource: str, request: Request, page: int = 1, limit: int = 25):
 mapping = {"prospects": ("prospects", "outreach_prospects"), "contacts": ("contacts", "outreach_contacts"), "campaigns": ("campaigns", "outreach_campaigns"), "sequences": ("sequences", "outreach_sequences"), "messages": ("messages", "outreach_messages"), "replies": ("replies", "outreach_replies"), "history": ("history", "outreach_history"), "suppression": ("suppression", "outreach_suppressions")}
 if resource not in mapping or page < 1 or limit < 1 or limit > 100: raise APIError(status.HTTP_422_UNPROCESSABLE_CONTENT, "INVALID_RESOURCE", "The Outreach resource or pagination is invalid.")
 return await page_collection(request, mapping[resource][0], mapping[resource][1], page, limit)
@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def campaign_detail(campaign_id: UUID, request: Request):
 app = app_for(request)
 try:
  value = await app.repository.get_campaign(campaign_id)
  if value is None: raise APIError(status.HTTP_404_NOT_FOUND, "NOT_FOUND", "The campaign was not found.")
  return response(value)
 finally: await app.aclose()
@router.get("/campaigns", response_model=OutreachCollectionResponse)
async def campaigns(request: Request): return await collection(request, "campaigns")
@router.get("/candidates", response_model=OutreachCollectionResponse)
async def candidates(request: Request): return await collection(request, "prospects")
@router.get("/messages", response_model=OutreachCollectionResponse)
async def messages(request: Request): return await collection(request, "messages")
@router.get("/replies", response_model=OutreachCollectionResponse)
async def reply_history(request: Request): return await collection(request, "replies")
@router.get("", response_model=OutreachSnapshotResponse)
async def snapshot(request:Request):
 app=app_for(request)
 try:
  value=await app.service.snapshot();keys=("prospects","contacts","campaigns","sequences","steps","messages","replies","followups","suppressions","history","analytics","gmail_configured","live_send_enabled","sender_email","reply_provider_configured","provider_name")
  return response({key:value[key] for key in keys})
 finally:await app.aclose()
@router.post("/campaigns",response_model=CampaignResponse,status_code=status.HTTP_201_CREATED)
async def campaign(payload:CampaignCreate,request:Request):
 app=app_for(request)
 try:return response(await app.service.create_campaign(CreateCampaignRequest(**payload.model_dump())))
 finally:await app.aclose()
@router.post("/candidates",response_model=CandidateResponse,status_code=status.HTTP_201_CREATED)
async def candidate(payload:CandidateCreate,request:Request):
 app=app_for(request)
 try:return response(await app.service.add_candidate(AddCandidateRequest(**payload.model_dump())))
 finally:await app.aclose()
@router.post("/messages/prepare",response_model=PreparedMessageResponse,status_code=status.HTTP_201_CREATED)
async def prepare(payload:MessagePrepare,request:Request):
 app=app_for(request)
 try:
  recipient=await app.service.add_recipient(AddRecipientRequest(campaign_id=payload.campaign_id,candidate_id=payload.candidate_id))
  return response(await app.service.prepare_message(PrepareMessageRequest(campaign_id=payload.campaign_id,recipient_id=recipient.recipient_id,subject_template=payload.subject_template,body_template=payload.body_template,sequence_step=payload.sequence_step)))
 finally:await app.aclose()
@router.post("/messages/{message_id}/send",response_model=SentMessageResponse)
async def send(message_id:UUID,payload:MessageSendConfirmation,request:Request):
 app=app_for(request)
 try:
  message=await app.repository.get_message(message_id)
  if message is None:raise APIError(status.HTTP_404_NOT_FOUND,"NOT_FOUND","The prepared message was not found.")
  recipient=await app.repository.get_recipient(message.recipient_id);candidate=await app.repository.get_candidate(recipient.candidate_id) if recipient else None
  sender=str(getattr(app.service._delivery,"sender_email","") or "")
  exact=payload.confirmed and candidate is not None and payload.recipient.casefold()==str(candidate.email).casefold() and payload.sender.casefold()==sender.casefold() and payload.subject==message.subject and payload.body==message.body and payload.campaign_id==message.campaign_id and payload.sequence_step==message.sequence_step
  if not exact:raise APIError(status.HTTP_409_CONFLICT,"CONFIRMATION_MISMATCH","The exact send preview was not confirmed.")
  if not payload.dry_run and not bool(getattr(app.service._delivery,"live_enabled",False)):raise APIError(status.HTTP_409_CONFLICT,"LIVE_SEND_DISABLED","Gmail live sending is disabled.")
  return response(await app.service.send(SendMessageRequest(message_id=message_id,dry_run=payload.dry_run)))
 finally:await app.aclose()
@router.post("/replies/check",response_model=RepliesResponse)
async def replies(request:Request):
 app=app_for(request)
 try:
  if app.service._reply_provider is None:raise APIError(status.HTTP_409_CONFLICT,"PROVIDER_NOT_CONFIGURED","Gmail reply checking is not configured.")
  return response(list(await app.service.sync_replies()))
 finally:await app.aclose()
