from __future__ import annotations
import re
from src.competitor_gap.domain import ContentGapType,KeywordGap
from src.content_intelligence.domain import *
class ContentIntelligenceService:
 @staticmethod
 def intent(gap):
  q=gap.keyword.lower();titles=" ".join(r.url.lower() for r in gap.serp);signals=[]
  info=bool(re.search(r"\b(how|guide|what|ideas|tips)\b",q)) or any(x in titles for x in ("/blog","/guide","/article"));trans=bool(re.search(r"\b(buy|shop|price|sale)\b",q)) or any(x in titles for x in ("/product","/collections","/shop"));commercial=bool(re.search(r"\b(best|top|review|compare)\b",q))
  if info:signals.append("Query wording or observed URLs contain guide/article patterns")
  if trans:signals.append("Query wording or observed URLs contain product/shop patterns")
  if commercial:signals.append("Query wording contains comparison or evaluation language")
  label=SearchIntent.MIXED if sum((info,trans,commercial))>1 else SearchIntent.INFORMATIONAL if info else SearchIntent.TRANSACTIONAL if trans else SearchIntent.COMMERCIAL_INVESTIGATION if commercial else SearchIntent.UNCLEAR
  return label,tuple(signals or ["Observed evidence does not support a confident intent classification"])
 def generate(self,gap:KeywordGap,all_gaps=(),page=None,links=()):
  mode=ContentMode.OPTIMIZE_EXISTING_PAGE if gap.mapped_page else ContentMode.POSSIBLE_NEW_CONTENT if gap.content_gap==ContentGapType.POSSIBLE_NEW_CONTENT_GAP else ContentMode.INSUFFICIENT_EVIDENCE
  intent,intent_evidence=self.intent(gap);support=[];tokens=set(re.findall(r"[a-z0-9]+",gap.keyword.lower()))
  for item in all_gaps:
   if item.keyword==gap.keyword:continue
   related=(gap.mapped_page and item.mapped_page==gap.mapped_page) or len(tokens&set(re.findall(r"[a-z0-9]+",item.keyword.lower())))>=2
   if related:support.append(SupportingQuery(query=item.keyword,source="GSC + TRACKED_SERP" if item.gsc_impressions is not None else "TRACKED_SERP",impressions=item.gsc_impressions,clicks=item.gsc_clicks,gsc_average_position=item.gsc_average_position,tracked_position=item.target_position,gap_type=item.gap_type.value))
   if len(support)>=10:break
  issues=tuple(page.issues) if page else ();pre=[]
  if page:
   if page.indexability.value!="INDEXABLE":pre.append(f"Review {page.indexability.value} indexability signal before or alongside content work.")
   if page.status_code is None or page.status_code>=400:pre.append(f"Resolve observed HTTP status {page.status_code or 'unreachable'} before content expansion.")
   if not page.title:pre.append("Add a descriptive title.")
   if not page.h1s:pre.append("Add a clear primary heading.")
  title_guidance=("Include the primary query concept naturally.","Differentiate the page from observed SERP competitors without copying their titles.","Align wording with the observed intent evidence.")
  suggested=f"{gap.keyword.title()} | Practical Guide" if intent==SearchIntent.INFORMATIONAL else f"{gap.keyword.title()} | Explore Options"
  meta_guidance=("Clarify the page's value proposition and relevance to the primary query.","Review snippet alignment; no CTR improvement is guaranteed.") if gap.gsc_ctr is not None and gap.gsc_ctr<0.03 else ("Describe the page accurately and align it with the observed query intent.",)
  h2=[]
  for item in support[:6]:h2.append(f"Consider covering: {item.query.title()}")
  if not h2:h2=["Key considerations and options","Frequently asked questions"]
  recs=[]
  if page and page.inlink_count<=2:
   for link in links:
    if link.target_url==page.normalized_url and link.source_url!=page.normalized_url:recs.append(InternalLinkRecommendation(source_page=link.source_url,target_page=page.normalized_url,evidence=f"Target has {page.inlink_count} crawled inlinks",suggested_anchor_concept=gap.keyword,reason="Potential internal-link support candidate; ranking improvement is not guaranteed."))
    if len(recs)>=5:break
  observations=[]
  if gap.competitors_ahead:observations.append(f"{gap.competitors_ahead} observed competitor domains rank ahead in the tracked SERP.")
  if not support:observations.append("No additional reliably related persisted query was found.")
  search=gap.score.gsc;serp=gap.score.serp;readiness=min(20,len(pre)*8+(10 if page and page.inlink_count<=2 else 0));engagement=gap.score.ga4;gap_score=15 if mode==ContentMode.POSSIBLE_NEW_CONTENT else 10 if mode==ContentMode.OPTIMIZE_EXISTING_PAGE else 0;total=min(100,search+serp+readiness+engagement+gap_score);priority=ContentPriority.CRITICAL if total>=85 and pre else ContentPriority.HIGH if total>=65 else ContentPriority.MEDIUM if total>=35 else ContentPriority.LOW
  actions=list(pre);actions+=(["Review title and metadata alignment.","Expand or refine sections supported by the query and SERP evidence."] if mode==ContentMode.OPTIMIZE_EXISTING_PAGE else ["Validate search intent before considering a dedicated page."]);actions+=(["Add contextually compatible internal links from the observed source pages."] if recs else []);actions.append("Monitor tracked SERP position and GSC performance after any change without assuming causation.")
  return ContentBrief(target_url=gap.mapped_page,mode=mode,primary_query=gap.keyword,primary_query_reason="Explicit selected tracked keyword with persisted competitor-gap evidence.",priority=priority,score=ContentScore(search=search,serp=serp,page_readiness=readiness,engagement=engagement,gap=gap_score,total=total),gsc_impressions=gap.gsc_impressions,gsc_clicks=gap.gsc_clicks,gsc_ctr=gap.gsc_ctr,gsc_average_position=gap.gsc_average_position,tracked_position=gap.target_position,competitors_ahead=gap.competitors_ahead,intent=intent,intent_evidence=intent_evidence,current_title=page.title if page else None,current_meta=page.meta_description if page else None,current_h1=page.h1s[0] if page and page.h1s else None,crawl_depth=page.depth if page else None,inlinks=page.inlink_count if page else None,technical_issues=issues,supporting_queries=tuple(support),serp_competitors=tuple(SERPCompetitor(domain=r.domain,position=r.position,url=r.url,title=r.title,snippet=r.snippet) for r in gap.serp if not r.is_target),content_gap_observations=tuple(observations),title_guidance=title_guidance,suggested_title=suggested,meta_guidance=meta_guidance,suggested_h1=gap.keyword.title(),h2_sections=tuple(h2),internal_links=tuple(recs),technical_preconditions=tuple(pre),actions=tuple(f"{i+1}. {a}" for i,a in enumerate(actions)),evidence=tuple(BriefEvidence(source="COMPETITOR_GAP",observation=e) for e in gap.evidence),limitations=("Search volume, keyword difficulty, competitor traffic, authority metrics, and guaranteed outcomes are not available.","Intent is a cautious observation from persisted query and SERP patterns."))
 @staticmethod
 def markdown(b):
  def lines(values):return "\n".join(f"- {v}" for v in values) or "- NOT AVAILABLE"
  return f"# SEO Content Brief: {b.primary_query}\n\n## Overview\n- Mode: {b.mode.value}\n- Target URL: {b.target_url or 'NOT AVAILABLE'}\n- Priority: {b.priority.value}\n- Score: {b.score.total}/100\n\n## Intent observation\n- {b.intent.value}\n{lines(b.intent_evidence)}\n\n## Title guidance\n{lines(b.title_guidance)}\n- Suggested copy: {b.suggested_title}\n\n## Meta guidance\n{lines(b.meta_guidance)}\n\n## Heading outline\n- H1: {b.suggested_h1}\n{lines(b.h2_sections)}\n\n## Technical preconditions\n{lines(b.technical_preconditions)}\n\n## Action plan\n{lines(b.actions)}\n\n## Limitations\n{lines(b.limitations)}\n"
