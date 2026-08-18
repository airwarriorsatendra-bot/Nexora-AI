"""Immutable evidence models for tracked-SERP competitor gap intelligence."""
from __future__ import annotations
from decimal import Decimal
from enum import Enum
from pydantic import ConfigDict,Field
from src.shared.base.base_model import NexoraModel
class KeywordGapType(str,Enum):
 MISSING="MISSING";COMPETITOR_AHEAD="COMPETITOR_AHEAD";TARGET_AHEAD="TARGET_AHEAD";SHARED_TOP_10="SHARED_TOP_10";COMPETITOR_TOP_3_TARGET_OUTSIDE_TOP_10="COMPETITOR_TOP_3_TARGET_OUTSIDE_TOP_10"
class ContentGapType(str,Enum): EXISTING_PAGE_OPTIMIZATION="EXISTING_PAGE_OPTIMIZATION";POSSIBLE_NEW_CONTENT_GAP="POSSIBLE_NEW_CONTENT_GAP";INSUFFICIENT_EVIDENCE="INSUFFICIENT_EVIDENCE"
class GapPriority(str,Enum): CRITICAL="CRITICAL";HIGH="HIGH";MEDIUM="MEDIUM";LOW="LOW"
class CompetitorDomainObservation(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");domain:str;keywords_observed:int;serp_appearances:int;top_3_appearances:int;top_10_appearances:int;top_20_appearances:int;best_observed_position:int;average_observed_position:Decimal;observed_top_10_coverage:Decimal;target_overlap:int
class CompetitorPageObservation(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");domain:str;url:str;keywords_observed:int;best_observed_rank:int;top_10_appearances:int
class CompetitiveScoreBreakdown(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");gsc:int=0;serp:int=0;site:int=0;ga4:int=0;total:int=Field(ge=0,le=100)
class ObservedSERPRow(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");position:int;domain:str;url:str;title:str="";snippet:str="";is_target:bool=False
class KeywordGap(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");keyword:str;gap_type:KeywordGapType;flags:tuple[str,...]=();target_domain:str;target_position:int|None=None;target_position_label:str;best_competitor:str;competitor_position:int;competitors_ahead:int;search_depth:int;gsc_average_position:Decimal|None=None;gsc_impressions:int|None=None;gsc_clicks:int|None=None;gsc_ctr:Decimal|None=None;mapped_page:str|None=None;content_gap:ContentGapType;score:CompetitiveScoreBreakdown;priority:GapPriority;evidence:tuple[str,...];recommended_action:str;serp:tuple[ObservedSERPRow,...]=()
class PageGapSummary(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");target_page:str;gap_keywords:int;competitor_ahead_keywords:int;gsc_clicks:int;gsc_impressions:int;gsc_ctr:Decimal|None=None;ga4_sessions:Decimal|None=None;ga4_engagement_rate:Decimal|None=None;inlinks:int|None=None;depth:int|None=None;technical_issues:int|None=None;score:int=Field(ge=0,le=100)
class CompetitorTrend(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");keyword:str;domain:str;trend:str;previous_position:int|None=None;current_position:int|None=None;evidence:str
class CompetitorGapReport(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");target_domain:str;competitors:tuple[CompetitorDomainObservation,...]=();keyword_gaps:tuple[KeywordGap,...]=();page_gaps:tuple[PageGapSummary,...]=();competitor_pages:tuple[CompetitorPageObservation,...]=();trends:tuple[CompetitorTrend,...]=();notes:tuple[str,...]=()
