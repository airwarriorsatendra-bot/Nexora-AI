from pydantic import ConfigDict,Field
from src.meta_ads.domain import MetaAccount,MetaAudit,MetaCampaign,Period
from src.shared.base.base_model import NexoraModel
class MetaAdsAuditRequest(NexoraModel):
 model_config=ConfigDict(frozen=True,extra='forbid');account:MetaAccount;period:Period;campaigns:list[MetaCampaign]=Field(min_length=1);source:str=Field(default='IMPORT',pattern='^(IMPORT|TEST_FIXTURE)$')
class MetaAdsAuditResponse(NexoraModel):success:bool;audit:MetaAudit|None=None;errors:list[str]=Field(default_factory=list);message:str=''
