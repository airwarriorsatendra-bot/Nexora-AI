from __future__ import annotations
from decimal import Decimal
from enum import Enum
from pydantic import ConfigDict,Field
from src.shared.base.base_model import NexoraModel
class ContentMode(str,Enum):OPTIMIZE_EXISTING_PAGE="OPTIMIZE_EXISTING_PAGE";POSSIBLE_NEW_CONTENT="POSSIBLE_NEW_CONTENT";INSUFFICIENT_EVIDENCE="INSUFFICIENT_EVIDENCE"
class SearchIntent(str,Enum):INFORMATIONAL="INFORMATIONAL";COMMERCIAL_INVESTIGATION="COMMERCIAL_INVESTIGATION";TRANSACTIONAL="TRANSACTIONAL";NAVIGATIONAL="NAVIGATIONAL";MIXED="MIXED";UNCLEAR="UNCLEAR"
class ContentPriority(str,Enum):CRITICAL="CRITICAL";HIGH="HIGH";MEDIUM="MEDIUM";LOW="LOW"
class BriefEvidence(NexoraModel):model_config=ConfigDict(frozen=True,extra="forbid");source:str;observation:str
class SupportingQuery(NexoraModel):model_config=ConfigDict(frozen=True,extra="forbid");query:str;source:str;impressions:int|None=None;clicks:int|None=None;gsc_average_position:Decimal|None=None;tracked_position:int|None=None;gap_type:str|None=None
class ContentScore(NexoraModel):model_config=ConfigDict(frozen=True,extra="forbid");search:int=0;serp:int=0;page_readiness:int=0;engagement:int=0;gap:int=0;total:int=Field(ge=0,le=100)
class SERPCompetitor(NexoraModel):model_config=ConfigDict(frozen=True,extra="forbid");domain:str;position:int;url:str;title:str="";snippet:str=""
class InternalLinkRecommendation(NexoraModel):model_config=ConfigDict(frozen=True,extra="forbid");source_page:str;target_page:str;evidence:str;suggested_anchor_concept:str;reason:str
class ContentBrief(NexoraModel):
 model_config=ConfigDict(frozen=True,extra="forbid");target_url:str|None=None;mode:ContentMode;primary_query:str;primary_query_reason:str;priority:ContentPriority;score:ContentScore;gsc_impressions:int|None=None;gsc_clicks:int|None=None;gsc_ctr:Decimal|None=None;gsc_average_position:Decimal|None=None;tracked_position:int|None=None;competitors_ahead:int=0;intent:SearchIntent;intent_evidence:tuple[str,...]=();current_title:str|None=None;current_meta:str|None=None;current_h1:str|None=None;crawl_depth:int|None=None;inlinks:int|None=None;technical_issues:tuple[str,...]=();supporting_queries:tuple[SupportingQuery,...]=();serp_competitors:tuple[SERPCompetitor,...]=();content_gap_observations:tuple[str,...]=();title_guidance:tuple[str,...]=();suggested_title:str|None=None;meta_guidance:tuple[str,...]=();suggested_h1:str;h2_sections:tuple[str,...]=();internal_links:tuple[InternalLinkRecommendation,...]=();technical_preconditions:tuple[str,...]=();actions:tuple[str,...]=();aeo_opportunities:tuple[str,...]=();geo_readiness:tuple[str,...]=();question_opportunities:tuple[str,...]=();direct_answer_suggestions:tuple[str,...]=();faq_opportunities:tuple[str,...]=();entity_source_support:tuple[str,...]=();evidence:tuple[BriefEvidence,...]=();limitations:tuple[str,...]=()
