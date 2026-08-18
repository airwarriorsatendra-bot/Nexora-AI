from __future__ import annotations
from datetime import UTC,datetime
from enum import Enum
from uuid import UUID,uuid4
from pydantic import ConfigDict,Field
from src.shared.base.base_model import NexoraModel
class ProviderClassification(str,Enum):GROUNDED_WITH_CITATIONS="GROUNDED_WITH_CITATIONS";GROUNDED_WITH_STRUCTURED_CITATIONS="GROUNDED_WITH_STRUCTURED_CITATIONS";GROUNDED_WITH_SOURCE_URLS="GROUNDED_WITH_SOURCE_URLS";GROUNDED_WITHOUT_STRUCTURED_CITATIONS="GROUNDED_WITHOUT_STRUCTURED_CITATIONS";UNGROUNDED_MODEL_RESPONSE="UNGROUNDED_MODEL_RESPONSE";UNAVAILABLE="UNAVAILABLE"
class ObservationState(str,Enum):SUCCESS="SUCCESS";PROVIDER_ERROR="PROVIDER_ERROR";TIMEOUT="TIMEOUT";RATE_LIMITED="RATE_LIMITED";UNAVAILABLE="UNAVAILABLE";EMPTY_RESPONSE="EMPTY_RESPONSE";GROUNDING_UNAVAILABLE="GROUNDING_UNAVAILABLE"
class PromptCategory(str,Enum):BRANDED="BRANDED";CATEGORY_DISCOVERY="CATEGORY_DISCOVERY";COMMERCIAL_INVESTIGATION="COMMERCIAL_INVESTIGATION";QUESTION_AEO="QUESTION_AEO";COMPARISON="COMPARISON";PRODUCT_SERVICE_DISCOVERY="PRODUCT_SERVICE_DISCOVERY";LOCAL="LOCAL";CUSTOM="CUSTOM"
class VisibilityChange(str,Enum):NEWLY_VISIBLE="NEWLY_VISIBLE";CONSISTENTLY_VISIBLE="CONSISTENTLY_VISIBLE";LOST_VISIBILITY="LOST_VISIBILITY";INTERMITTENT="INTERMITTENT";NOT_OBSERVED="NOT_OBSERVED";NEW_CITATION="NEW_CITATION";LOST_CITATION="LOST_CITATION"
class ProviderCapability(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");provider:str;model:str;classification:ProviderClassification;web_grounding_supported:bool=False;citations_supported:bool=False;source_urls_supported:bool=False;response_text_supported:bool=True;usage_metadata_supported:bool=False;temperature_control_supported:bool=False;seed_supported:bool=False;location_context_supported:bool=False;language_context_supported:bool=False
class MonitoredPrompt(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");prompt_id:UUID=Field(default_factory=uuid4);text:str=Field(min_length=1,max_length=4000);category:PromptCategory=PromptCategory.CUSTOM;source:str="MANUAL";context:str="";active:bool=True
class VisibilityRequest(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");prompt:MonitoredPrompt;brand_name:str=Field(min_length=1);brand_aliases:tuple[str,...]=();target_domain:str=Field(min_length=1);competitors:dict[str,tuple[str,...]]={}
class Citation(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");url:str;title:str="";index:int=Field(ge=1);source_type:str="STRUCTURED_CITATION";provider_metadata:dict[str,str]={}
class ProviderResponse(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");provider:str;model:str;prompt:str;response_text:str;citations:tuple[Citation,...]=();provider_response_id:str|None=None;usage:dict[str,int]={};observed_at:datetime=Field(default_factory=lambda:datetime.now(UTC));classification:ProviderClassification;metadata:dict[str,str]={}
class Mention(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");name:str;matched_alias:str;count:int=Field(ge=1);first_offset:int=Field(ge=0);mention_order:int=Field(ge=1);excerpt:str
class CitationObservation(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");url:str;normalized_url:str="";domain:str;title:str="";index:int;source_type:str="STRUCTURED_CITATION";is_target:bool=False;competitor:str|None=None;provider_metadata:dict[str,str]={}
class AIVisibilityObservation(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");observation_id:UUID=Field(default_factory=uuid4);run_id:UUID;prompt_id:UUID;prompt:str;category:PromptCategory;provider:str;model:str;classification:ProviderClassification;state:ObservationState;response_text:str="";brand_mention:Mention|None=None;competitor_mentions:tuple[Mention,...]=();citations:tuple[CitationObservation,...]=();citation_tracking_available:bool=False;target_domain_cited:bool|None=None;target_urls_cited:tuple[str,...]=();first_target_citation_order:int|None=None;error_category:str|None=None;observed_at:datetime=Field(default_factory=lambda:datetime.now(UTC))
class AIVisibilityRun(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");run_id:UUID=Field(default_factory=uuid4);brand_name:str;target_domain:str;providers:tuple[str,...];prompt_count:int;repetitions:int=Field(default=1,ge=1,le=3);created_at:datetime=Field(default_factory=lambda:datetime.now(UTC));observations:tuple[AIVisibilityObservation,...]=()
class ProviderSummary(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");provider:str;model:str;successful_observations:int;brand_mention_coverage:float;citation_coverage:float|None=None;citation_denominator:int=0;competitor_mentions:int=0;mention_stability:float;sample_size:int
class VisibilityReport(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");run:AIVisibilityRun;provider_summaries:tuple[ProviderSummary,...]=();brand_mention_coverage:float=0;citation_coverage:float|None=None;citation_denominator:int=0;competitors_observed:int=0;target_domain_citations:int=0;actions:tuple[str,...]=();limitations:tuple[str,...]=()
