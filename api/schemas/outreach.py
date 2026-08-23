"""Outreach CRM HTTP contracts and explicit send confirmation."""
from __future__ import annotations
from uuid import UUID
from typing import Any
from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, RootModel
from src.core.enums import CampaignObjective
from api.schemas.pagination import PageMetadata

class CampaignCreate(BaseModel):
 model_config=ConfigDict(extra="forbid");name:str=Field(min_length=1,max_length=200);description:str=Field(default="",max_length=2000);objective:CampaignObjective=CampaignObjective.GENERAL
class CandidateCreate(BaseModel):
 model_config=ConfigDict(extra="forbid");website_url:HttpUrl;email:EmailStr;contact_name:str=Field(default="",max_length=200)
class MessagePrepare(BaseModel):
 model_config=ConfigDict(extra="forbid");campaign_id:UUID;candidate_id:UUID;subject_template:str=Field(min_length=1,max_length=300);body_template:str=Field(min_length=1,max_length=20000);sequence_step:int=Field(default=1,ge=1,le=20)
class MessageSendConfirmation(BaseModel):
 model_config=ConfigDict(extra="forbid");dry_run:bool=True;sender:str;recipient:EmailStr;subject:str;body:str;campaign_id:UUID;sequence_step:int=Field(ge=1,le=20);expected_send_count:int=Field(ge=1,le=1);confirmed:bool

class OutreachSnapshotResponse(RootModel[dict[str, Any]]): pass
class CampaignResponse(RootModel[dict[str, Any]]): pass
class CandidateResponse(RootModel[dict[str, Any]]): pass
class PreparedMessageResponse(RootModel[dict[str, Any]]): pass
class SentMessageResponse(RootModel[dict[str, Any]]): pass
class RepliesResponse(RootModel[list[dict[str, Any]]]): pass
class OutreachCollectionResponse(RootModel[list[dict[str, Any]]]): pass
class OutreachPage(BaseModel):
 model_config=ConfigDict(extra="forbid")
 items:list[dict[str,Any]]
 pagination:PageMetadata
