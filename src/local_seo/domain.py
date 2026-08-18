"""Evidence-preserving Local SEO 2.0 domain models."""
from __future__ import annotations
from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4
from pydantic import ConfigDict, Field, HttpUrl
from src.core.enums import Priority
from src.shared.base.base_model import NexoraModel
from src.shared.value_objects.location import Location

def now()->datetime:return datetime.now(UTC)
class FreshnessState(str,Enum):FRESH="FRESH";STALE="STALE";UNKNOWN="UNKNOWN"
class ProviderCapability(str,Enum):PROFILE_READ="PROFILE_READ";REVIEWS_READ="REVIEWS_READ";PERFORMANCE_READ="PERFORMANCE_READ";MEDIA_READ="MEDIA_READ";PROFILE_WRITE="PROFILE_WRITE";REVIEW_REPLY_WRITE="REVIEW_REPLY_WRITE"
class NAPState(str,Enum):CONSISTENT="CONSISTENT";NAME_MISMATCH="NAME_MISMATCH";ADDRESS_MISMATCH="ADDRESS_MISMATCH";PHONE_MISMATCH="PHONE_MISMATCH";MULTIPLE_MISMATCHES="MULTIPLE_MISMATCHES";INSUFFICIENT_EVIDENCE="INSUFFICIENT_EVIDENCE"
class ReviewActivityState(str,Enum):ACTIVE="ACTIVE";SLOW="SLOW";STALE="STALE";INSUFFICIENT_EVIDENCE="INSUFFICIENT_EVIDENCE"
class LocalResultType(str,Enum):ORGANIC="ORGANIC";LOCAL_PACK="LOCAL_PACK";MAPS="MAPS";OTHER="OTHER"
class LocalRankChange(str,Enum):NEW="NEW";IMPROVED="IMPROVED";DECLINED="DECLINED";UNCHANGED="UNCHANGED";LOST="LOST";REAPPEARED="REAPPEARED";INSUFFICIENT_HISTORY="INSUFFICIENT_HISTORY"
class CitationState(str,Enum):PRESENT_CONSISTENT="PRESENT_CONSISTENT";PRESENT_INCONSISTENT="PRESENT_INCONSISTENT";MISSING="MISSING";DUPLICATE_SUSPECTED="DUPLICATE_SUSPECTED";UNVERIFIED="UNVERIFIED";INSUFFICIENT_EVIDENCE="INSUFFICIENT_EVIDENCE"
class LocalPageState(str,Enum):HEALTHY="HEALTHY";MISSING_LOCAL_SIGNAL="MISSING_LOCAL_SIGNAL";WEAK_CONTENT="WEAK_CONTENT";TECHNICAL_BLOCKER="TECHNICAL_BLOCKER";LOW_INTERNAL_LINK_SUPPORT="LOW_INTERNAL_LINK_SUPPORT";NO_QUERY_EVIDENCE="NO_QUERY_EVIDENCE";INSUFFICIENT_EVIDENCE="INSUFFICIENT_EVIDENCE"

class LocalBusiness(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");business_id:UUID=Field(default_factory=uuid4);name:str=Field(min_length=1,max_length=300);website:HttpUrl;phone:str=Field(default="",max_length=50);location:Location;primary_category:str=Field(default="",max_length=150)
class BusinessLocation(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");location_id:str=Field(min_length=1,max_length=255);business_id:UUID;account_id:str|None=None;business_name:str="";primary_category:str="";additional_categories:tuple[str,...]=();address:str="";locality:str="";administrative_area:str="";postal_code:str="";country:str="";phone:str="";website:str|None=None;service_area:tuple[str,...]=();latitude:float|None=Field(default=None,ge=-90,le=90);longitude:float|None=Field(default=None,ge=-180,le=180);regular_hours:dict[str,str]=Field(default_factory=dict);special_hours:dict[str,str]=Field(default_factory=dict);profile_status:str|None=None;source:str="MANUAL";provider:str="MANUAL";observed_at:datetime=Field(default_factory=now);freshness:FreshnessState=FreshnessState.UNKNOWN
class NAPEvidence(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");evidence_id:UUID=Field(default_factory=uuid4);location_id:str;source:str;name:str|None=None;address:str|None=None;phone:str|None=None;normalized_name:str|None=None;normalized_address:str|None=None;normalized_phone:str|None=None;observed_at:datetime=Field(default_factory=now)
class NAPAssessment(NexoraModel):
 location_id:str;state:NAPState;evidence_count:int=Field(ge=0);comparable_fields:int=Field(ge=0);explanation:str;assessed_at:datetime=Field(default_factory=now)
class Citation(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");source:str=Field(min_length=1,max_length=100);business_name:str="";address:str="";phone:str="";website:HttpUrl|None=None
class LocalCitation(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");citation_id:UUID=Field(default_factory=uuid4);location_id:str;directory:str;listing_url:str|None=None;business_name:str|None=None;address:str|None=None;phone:str|None=None;website_url:str|None=None;category:str|None=None;state:CitationState=CitationState.UNVERIFIED;source:str="MANUAL";provider:str="MANUAL";observed_at:datetime=Field(default_factory=now)
class CitationTarget(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");target_id:UUID=Field(default_factory=uuid4);location_id:str;directory:str;configured_at:datetime=Field(default_factory=now)
class LocalReview(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");review_id:str;location_id:str;rating:float=Field(ge=1,le=5);text:str="";reviewer_name:str|None=None;reviewed_at:datetime|None=None;owner_response:str|None=None;owner_response_at:datetime|None=None;provider:str;observed_at:datetime=Field(default_factory=now)
class ReviewSummary(NexoraModel):
 location_id:str;average_rating:float|None=None;review_count:int=0;reviews_30d:int=0;reviews_90d:int=0;reviews_365d:int=0;response_count:int=0;response_rate:float|None=None;unanswered:int=0;velocity_30d:float|None=None;velocity_90d:float|None=None;latest_review_age_days:int|None=None;median_review_age_days:float|None=None;median_response_hours:float|None=None;activity_state:ReviewActivityState=ReviewActivityState.INSUFFICIENT_EVIDENCE
class LocalRankObservation(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");observation_id:UUID=Field(default_factory=uuid4);location_id:str;query:str;location_descriptor:str;device:str;engine:str="google";result_type:LocalResultType;position:int|None=Field(default=None,ge=1);observed_url:str|None=None;observed_domain:str|None=None;latitude:float|None=Field(default=None,ge=-90,le=90);longitude:float|None=Field(default=None,ge=-180,le=180);provider:str="MANUAL";observed_at:datetime=Field(default_factory=now)
class LocalRankComparison(NexoraModel):
 current:LocalRankObservation;previous_position:int|None=None;change:LocalRankChange;movement:int|None=None
class LocalQueryEvidence(NexoraModel):
 query:str;location_modifier:str|None=None;gsc_clicks:int|None=None;gsc_impressions:int|None=None;gsc_ctr:float|None=None;gsc_average_position:float|None=None;tracked_position:int|None=None;tracked_result_type:LocalResultType|None=None;landing_page:str|None=None;opportunity:str|None=None;source:str="GOOGLE_SEARCH_CONSOLE"
class LocalLandingPage(NexoraModel):
 url:str;location_id:str|None=None;service:str|None=None;http_status:int|None=None;indexable:bool|None=None;canonical:str|None=None;title:str="";h1:str="";schema_types:tuple[str,...]=();word_count:int|None=None;crawl_depth:int|None=None;internal_links:int|None=None;gsc_impressions:int|None=None;tracked_position:int|None=None;content_brief_available:bool=False;state:LocalPageState=LocalPageState.INSUFFICIENT_EVIDENCE;provenance:tuple[str,...]=()
class LocalCompetitor(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");competitor_id:UUID=Field(default_factory=uuid4);location_id:str;domain:str;business_name:str|None=None;source:str;observed_query:str|None=None;observed_rank:int|None=Field(default=None,ge=1);result_type:LocalResultType|None=None;rating:float|None=Field(default=None,ge=1,le=5);review_count:int|None=Field(default=None,ge=0);domain_authority:float|None=None;page_authority:float|None=None;citation_evidence:int|None=None;observed_at:datetime=Field(default_factory=now)
class LocalOpportunity(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");opportunity_id:UUID=Field(default_factory=uuid4);opportunity_type:str;location_id:str|None=None;priority:Priority;score:int=Field(ge=0,le=100);title:str;evidence:str;reason:str;recommended_action:str;provenance:tuple[str,...];handoff:str|None=None;observed_at:datetime=Field(default_factory=now)
class LocalHistoryEvent(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");event_id:UUID=Field(default_factory=uuid4);location_id:str|None=None;evidence_type:str;provider:str;detail:str;observed_at:datetime=Field(default_factory=now)
class LocalIssue(NexoraModel):code:str;category:str;severity:Priority;title:str;description:str;evidence:str="";recommendation:str="";source:str="website"
class LocalSEOAudit(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");audit_id:UUID=Field(default_factory=uuid4);business:LocalBusiness;audited_at:datetime=Field(default_factory=now);overall_score:float=Field(ge=0,le=100);category_scores:dict[str,float]=Field(default_factory=dict);issues:list[LocalIssue]=Field(default_factory=list);signals:dict[str,str|int|bool|None]=Field(default_factory=dict);citations:list[Citation]=Field(default_factory=list)
class LocalSEOIntelligence(NexoraModel):
 locations:tuple[BusinessLocation,...]=();nap_evidence:tuple[NAPEvidence,...]=();nap_assessments:tuple[NAPAssessment,...]=();reviews:tuple[LocalReview,...]=();review_summaries:tuple[ReviewSummary,...]=();ranks:tuple[LocalRankComparison,...]=();queries:tuple[LocalQueryEvidence,...]=();landing_pages:tuple[LocalLandingPage,...]=();citations:tuple[LocalCitation,...]=();citation_targets:tuple[CitationTarget,...]=();competitors:tuple[LocalCompetitor,...]=();opportunities:tuple[LocalOpportunity,...]=();history:tuple[LocalHistoryEvent,...]=();generated_at:datetime=Field(default_factory=now)
