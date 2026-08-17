"""Runtime inputs and results for Local SEO audits."""
from __future__ import annotations
from pydantic import ConfigDict, Field
from src.local_seo.domain import Citation,LocalBusiness,LocalSEOAudit
from src.shared.base.base_model import NexoraModel
class LocalSEOAuditRequest(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid")
 business:LocalBusiness; citations:list[Citation]=Field(default_factory=list)
class LocalSEOAuditResponse(NexoraModel):
 success:bool; audit:LocalSEOAudit|None=None; errors:list[str]=Field(default_factory=list); message:str=""
