"""Validated Google Ads imported-snapshot domain."""
from __future__ import annotations
from datetime import UTC,date,datetime
from decimal import Decimal
from uuid import UUID,uuid4
from pydantic import ConfigDict,Field,model_validator
from src.core.enums import Priority
from src.shared.base.base_model import NexoraModel
def now():return datetime.now(UTC)
class ReportingPeriod(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid")
 date_from:date;date_to:date
 @model_validator(mode="after")
 def valid(self):
  if self.date_to<self.date_from:raise ValueError("date_to must not precede date_from")
  return self
class GoogleAdsAccount(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid")
 customer_id:str=Field(min_length=1,max_length=50);descriptive_name:str="";currency_code:str=Field(min_length=3,max_length=3);timezone:str=""
class GoogleAdsCampaign(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid")
 campaign_id:str=Field(min_length=1);name:str=Field(min_length=1);channel_type:str="OTHER";status:str="UNKNOWN";budget:Decimal|None=Field(default=None,ge=0);impressions:int=Field(ge=0);clicks:int=Field(ge=0);cost:Decimal=Field(ge=0);conversions:Decimal=Field(ge=0);conversion_value:Decimal=Field(ge=0)
 @property
 def ctr(self):return None if not self.impressions else Decimal(self.clicks)/Decimal(self.impressions)
 @property
 def average_cpc(self):return None if not self.clicks else self.cost/Decimal(self.clicks)
 @property
 def cpa(self):return None if not self.conversions else self.cost/self.conversions
 @property
 def roas(self):return None if not self.cost else self.conversion_value/self.cost
class GoogleAdsRecommendation(NexoraModel):
 recommendation_id:UUID=Field(default_factory=uuid4);campaign_id:str;category:str;severity:Priority;title:str;evidence:str;suggested_action:str;confidence:Decimal=Field(ge=0,le=1);created_at:datetime=Field(default_factory=now)
class GoogleAdsAudit(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid")
 audit_id:UUID=Field(default_factory=uuid4);account:GoogleAdsAccount;period:ReportingPeriod;source:str;campaigns:list[GoogleAdsCampaign];recommendations:list[GoogleAdsRecommendation]=Field(default_factory=list);captured_at:datetime=Field(default_factory=now)
