"""Google Ads import/audit runtime DTOs."""
from __future__ import annotations
from pydantic import ConfigDict,Field
from src.google_ads.domain import GoogleAdsAccount,GoogleAdsAudit,GoogleAdsCampaign,ReportingPeriod
from src.shared.base.base_model import NexoraModel
class GoogleAdsAuditRequest(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid")
 account:GoogleAdsAccount;period:ReportingPeriod;campaigns:list[GoogleAdsCampaign]=Field(min_length=1);source:str=Field(default="IMPORT",pattern="^(IMPORT|TEST_FIXTURE)$")
class GoogleAdsAuditResponse(NexoraModel):
 success:bool;audit:GoogleAdsAudit|None=None;errors:list[str]=Field(default_factory=list);message:str=""
