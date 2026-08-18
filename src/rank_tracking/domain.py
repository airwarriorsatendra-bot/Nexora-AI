"""Typed models for point-in-time SERP observations, separate from GSC position."""
from __future__ import annotations
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4
from pydantic import ConfigDict, Field, field_validator, model_validator
from src.shared.base.base_model import NexoraModel
class Device(str, Enum): DESKTOP="desktop"; MOBILE="mobile"
class RankChangeType(str, Enum): BASELINE="BASELINE"; IMPROVED="IMPROVED"; DECLINED="DECLINED"; STABLE="STABLE"; NEWLY_RANKING="NEWLY_RANKING"; LOST="LOST"
class TrackingContext(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid"); country:str=Field(default="US",min_length=2,max_length=2); language:str=Field(default="en",min_length=2,max_length=8); device:Device=Device.DESKTOP; search_engine:str="google"; location:str|None=None
 @field_validator("country")
 @classmethod
 def upper(cls,v):return v.upper()
class TrackedKeyword(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid"); keyword_id:UUID=Field(default_factory=uuid4); keyword:str=Field(min_length=1,max_length=256); target_domain:str=Field(min_length=1,max_length=253); target_url:str|None=None; context:TrackingContext=Field(default_factory=TrackingContext); active:bool=True; tags:tuple[str,...]=(); gsc_average_position:Decimal|None=Field(default=None,ge=0); gsc_clicks:int|None=Field(default=None,ge=0); gsc_impressions:int|None=Field(default=None,ge=0); created_at:datetime=Field(default_factory=lambda:datetime.now(UTC)); updated_at:datetime=Field(default_factory=lambda:datetime.now(UTC))
 @model_validator(mode="after")
 def normalize(self):
  object.__setattr__(self,"keyword"," ".join(self.keyword.split())); d=self.target_domain.strip().lower().removeprefix("https://").removeprefix("http://").split("/")[0].removeprefix("www.");object.__setattr__(self,"target_domain",d);return self
class SERPResult(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid"); position:int=Field(ge=1); title:str=""; url:str=Field(min_length=1); domain:str=Field(min_length=1); snippet:str=""; result_type:str="organic"
class RankCheck(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid"); check_id:UUID=Field(default_factory=uuid4); keyword_id:UUID; keyword:str; context:TrackingContext; depth:int=Field(ge=1,le=100); provider:str; results:tuple[SERPResult,...]=(); target_position:int|None=Field(default=None,ge=1); checked_at:datetime=Field(default_factory=lambda:datetime.now(UTC)); source:str="SERP_PROVIDER"
 @property
 def position_label(self):return str(self.target_position) if self.target_position is not None else f"NOT_FOUND_IN_TOP_{self.depth}"
 @property
 def not_found_label(self):return None if self.target_position is not None else self.position_label
class RankChange(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid"); change_type:RankChangeType; previous_position:int|None=None; current_position:int|None=None; movement:int|None=None
class CompetitorObservation(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid"); domain:str; keywords_observed:int=Field(ge=0); top_3_appearances:int=Field(ge=0); top_10_appearances:int=Field(ge=0); average_observed_position:Decimal=Field(ge=1); best_observed_position:int=Field(ge=1)
