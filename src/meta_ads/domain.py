from __future__ import annotations
from datetime import UTC,date,datetime
from decimal import Decimal
from uuid import UUID,uuid4
from pydantic import ConfigDict,Field,model_validator
from src.core.enums import Priority
from src.shared.base.base_model import NexoraModel
class Period(NexoraModel):
 model_config=ConfigDict(frozen=True,extra='forbid');date_from:date;date_to:date
 @model_validator(mode='after')
 def v(self):
  if self.date_to<self.date_from:raise ValueError('invalid reporting period')
  return self
class MetaAccount(NexoraModel):
 model_config=ConfigDict(frozen=True,extra='forbid');ad_account_id:str=Field(min_length=1);name:str='';currency:str=Field(min_length=3,max_length=3);timezone:str=''
class MetaCampaign(NexoraModel):
 model_config=ConfigDict(frozen=True,extra='forbid');campaign_id:str=Field(min_length=1);name:str=Field(min_length=1);objective:str='';status:str='UNKNOWN';impressions:int=Field(ge=0);reach:int=Field(ge=0);clicks:int=Field(ge=0);spend:Decimal=Field(ge=0);conversions:Decimal=Field(ge=0);conversion_value:Decimal=Field(ge=0)
 @property
 def ctr(self):return None if not self.impressions else Decimal(self.clicks)/self.impressions
 @property
 def cpc(self):return None if not self.clicks else self.spend/self.clicks
 @property
 def cpm(self):return None if not self.impressions else self.spend*1000/self.impressions
 @property
 def cpa(self):return None if not self.conversions else self.spend/self.conversions
 @property
 def roas(self):return None if not self.spend else self.conversion_value/self.spend
 @property
 def frequency(self):return None if not self.reach else Decimal(self.impressions)/self.reach
class MetaRecommendation(NexoraModel):
 recommendation_id:UUID=Field(default_factory=uuid4);campaign_id:str;category:str;severity:Priority;title:str;evidence:str;suggested_action:str;confidence:Decimal=Field(ge=0,le=1)
class MetaAudit(NexoraModel):
 model_config=ConfigDict(frozen=True,extra='forbid');audit_id:UUID=Field(default_factory=uuid4);account:MetaAccount;period:Period;source:str;campaigns:list[MetaCampaign];recommendations:list[MetaRecommendation]=Field(default_factory=list);captured_at:datetime=Field(default_factory=lambda:datetime.now(UTC))
