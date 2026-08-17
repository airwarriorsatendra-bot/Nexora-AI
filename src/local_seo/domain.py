"""Immutable business, citation, and local-audit records."""
from __future__ import annotations
from datetime import UTC, datetime
from uuid import UUID, uuid4
from pydantic import ConfigDict, Field, HttpUrl
from src.core.enums import Priority
from src.shared.base.base_model import NexoraModel
from src.shared.value_objects.location import Location
def now() -> datetime: return datetime.now(UTC)
class LocalBusiness(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid")
 business_id:UUID=Field(default_factory=uuid4); name:str=Field(min_length=1,max_length=300); website:HttpUrl; phone:str=Field(default="",max_length=50); location:Location; primary_category:str=Field(default="",max_length=150)
class Citation(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid")
 source:str=Field(min_length=1,max_length=100); business_name:str=""; address:str=""; phone:str=""; website:HttpUrl|None=None
class LocalIssue(NexoraModel):
 code:str; category:str; severity:Priority; title:str; description:str; evidence:str=""; recommendation:str=""; source:str="website"
class LocalSEOAudit(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid")
 audit_id:UUID=Field(default_factory=uuid4); business:LocalBusiness; audited_at:datetime=Field(default_factory=now); overall_score:float=Field(ge=0,le=100); category_scores:dict[str,float]=Field(default_factory=dict); issues:list[LocalIssue]=Field(default_factory=list); signals:dict[str,str|int|bool|None]=Field(default_factory=dict); citations:list[Citation]=Field(default_factory=list)
