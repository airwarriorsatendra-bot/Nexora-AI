"""Deterministic competitor and keyword-gap analysis over persisted evidence."""
from __future__ import annotations
from collections import Counter,defaultdict
from decimal import Decimal
from urllib.parse import urlsplit
from src.competitor_gap.domain import *
from src.rank_tracking.domain import RankCheck,TrackedKeyword
class CompetitorGapService:
 GOOGLE_HOSTS={"google.com","www.google.com","support.google.com","accounts.google.com"}
 @staticmethod
 def host(value):return (urlsplit(value if "://" in value else "//"+value).hostname or "").lower().removeprefix("www.")
 @staticmethod
 def priority(score):return GapPriority.CRITICAL if score>=80 else GapPriority.HIGH if score>=60 else GapPriority.MEDIUM if score>=35 else GapPriority.LOW
 def analyze(self,target_domain,keywords,checks,histories=None,gsc_queries=None,ga4_pages=None,crawl_pages=None):
  target=self.host(target_domain);histories=histories or {};gsc_queries={k.casefold():v for k,v in (gsc_queries or {}).items()};ga4_pages=ga4_pages or {};crawl_pages=crawl_pages or {}
  keyword_by_id={k.keyword_id:k for k in keywords if self.host(k.target_domain)==target};latest={c.keyword_id:c for c in checks if c.keyword_id in keyword_by_id};domain_data=defaultdict(lambda:{"keywords":set(),"positions":[],"overlap":0});page_data=defaultdict(lambda:{"keywords":set(),"positions":[]});gaps=[];trends=[]
  for kid,check in latest.items():
   item=keyword_by_id[kid];by_domain={}
   for result in check.results:
    domain=self.host(result.domain or result.url)
    if not domain or domain==target or domain in self.GOOGLE_HOSTS or result.result_type!="organic":continue
    by_domain[domain]=min(result.position,by_domain.get(domain,999));page_data[(domain,result.url)]["keywords"].add(check.keyword);page_data[(domain,result.url)]["positions"].append(result.position)
   for domain,pos in by_domain.items():domain_data[domain]["keywords"].add(check.keyword);domain_data[domain]["positions"].append(pos);domain_data[domain]["overlap"]+=int(check.target_position is not None)
   if not by_domain:continue
   best_domain,best_pos=min(by_domain.items(),key=lambda x:(x[1],x[0]));target_pos=check.target_position;ahead=sum(pos<target_pos for pos in by_domain.values()) if target_pos else len(by_domain)
   flags=[]
   if target_pos is None:gap_type=KeywordGapType.COMPETITOR_TOP_3_TARGET_OUTSIDE_TOP_10 if best_pos<=3 and check.depth>=10 else KeywordGapType.MISSING
   elif best_pos<target_pos:gap_type=KeywordGapType.COMPETITOR_TOP_3_TARGET_OUTSIDE_TOP_10 if best_pos<=3 and target_pos>10 else KeywordGapType.COMPETITOR_AHEAD
   elif target_pos<=10 and best_pos<=10:gap_type=KeywordGapType.SHARED_TOP_10
   else:gap_type=KeywordGapType.TARGET_AHEAD
   if target_pos is not None and best_pos<target_pos:flags.append("COMPETITOR_AHEAD")
   if target_pos is not None and target_pos<=10 and best_pos<=10:flags.append("SHARED_TOP_10")
   gsc=gsc_queries.get(check.keyword.casefold());mapped=item.target_url
   content=ContentGapType.EXISTING_PAGE_OPTIMIZATION if mapped else ContentGapType.POSSIBLE_NEW_CONTENT_GAP if target_pos is None and bool(by_domain) else ContentGapType.INSUFFICIENT_EVIDENCE
   gsc_score=0;serp_score=15+min(25,ahead*5)+(20 if target_pos is None else 10 if best_pos<target_pos else 0);site_score=0;ga4_score=0;evidence=[f"Observed competitor {best_domain} at position {best_pos}",check.position_label]
   impressions=clicks=None;avg=ctr=None
   if gsc:
    impressions,clicks,avg,ctr=gsc;gsc_score=min(25,(10 if impressions>=100 else 5)+(10 if impressions>=1000 else 0)+(5 if avg and avg>3 else 0));evidence.append(f"Persisted GSC impressions: {impressions}")
   crawl=crawl_pages.get(mapped) if mapped else None
   if crawl:
    if crawl.inlink_count<=2:site_score+=10;evidence.append(f"Crawled inlinks: {crawl.inlink_count}")
    if crawl.depth>=3:site_score+=5;evidence.append(f"Observed crawl depth: {crawl.depth}")
    if crawl.issues:site_score+=5;evidence.append(f"Technical issue signals: {len(crawl.issues)}")
   ga4=ga4_pages.get(mapped) if mapped else None
   if ga4:
    ga4_score=10;evidence.append(f"URL-matched GA4 sessions: {ga4[0]}")
   total=min(100,gsc_score+serp_score+site_score+ga4_score)
   if target_pos is None and mapped:action="Evaluate the existing mapped page's relevance and optimization before considering new content."
   elif content==ContentGapType.POSSIBLE_NEW_CONTENT_GAP:action="Possible new content gap; validate search intent before creating a dedicated page."
   elif gsc and ctr is not None and ctr<Decimal("0.03") and target_pos and target_pos<=10:action="Review title, meta description, SERP presentation, content alignment, and internal linking."
   else:action="Review content alignment, internal linking, technical signals, and the observed competitor SERP presentation."
   gaps.append(KeywordGap(keyword=check.keyword,gap_type=gap_type,flags=tuple(flags),target_domain=target,target_position=target_pos,target_position_label=check.position_label,best_competitor=best_domain,competitor_position=best_pos,competitors_ahead=ahead,search_depth=check.depth,gsc_average_position=avg,gsc_impressions=impressions,gsc_clicks=clicks,gsc_ctr=ctr,mapped_page=mapped,content_gap=content,score=CompetitiveScoreBreakdown(gsc=gsc_score,serp=serp_score,site=site_score,ga4=ga4_score,total=total),priority=self.priority(total),evidence=tuple(evidence),recommended_action=action,serp=tuple(ObservedSERPRow(position=r.position,domain=self.host(r.domain or r.url),url=r.url,title=r.title,snippet=r.snippet,is_target=self.host(r.domain or r.url)==target) for r in check.results)))
   history=histories.get(kid,())
   if len(history)>=2 and history[0].context==history[-1].context and history[0].depth==history[-1].depth:
    old={self.host(r.domain or r.url):r.position for r in history[0].results};new={self.host(r.domain or r.url):r.position for r in history[-1].results}
    for domain in sorted((set(old)|set(new))-{target}):
     op,np=old.get(domain),new.get(domain)
     trend="ENTERED_TOP_10" if (op is None or op>10) and np is not None and np<=10 else "EXITED_TOP_10" if op is not None and op<=10 and (np is None or np>10) else "IMPROVING" if op and np and np<op else "DECLINING" if op and np and np>op else "STABLE"
     if trend!="STABLE":trends.append(CompetitorTrend(keyword=check.keyword,domain=domain,trend=trend,previous_position=op,current_position=np,evidence="Compatible tracked SERP observations; no causal interpretation."))
  total_keywords=max(1,len(latest));competitors=[]
  for domain,data in domain_data.items():
   pos=data["positions"];competitors.append(CompetitorDomainObservation(domain=domain,keywords_observed=len(data["keywords"]),serp_appearances=len(pos),top_3_appearances=sum(p<=3 for p in pos),top_10_appearances=sum(p<=10 for p in pos),top_20_appearances=sum(p<=20 for p in pos),best_observed_position=min(pos),average_observed_position=Decimal(sum(pos))/Decimal(len(pos)),observed_top_10_coverage=Decimal(sum(1 for p in pos if p<=10))/Decimal(total_keywords),target_overlap=data["overlap"]))
  pages=[CompetitorPageObservation(domain=d,url=u,keywords_observed=len(v["keywords"]),best_observed_rank=min(v["positions"]),top_10_appearances=sum(p<=10 for p in v["positions"])) for (d,u),v in page_data.items()]
  grouped=defaultdict(list)
  for gap in gaps:
   if gap.mapped_page:grouped[gap.mapped_page].append(gap)
  page_gaps=[]
  for url,items in grouped.items():
   crawl=crawl_pages.get(url);ga4=ga4_pages.get(url);impressions=sum(i.gsc_impressions or 0 for i in items);clicks=sum(i.gsc_clicks or 0 for i in items);page_gaps.append(PageGapSummary(target_page=url,gap_keywords=len(items),competitor_ahead_keywords=sum("COMPETITOR_AHEAD" in i.flags for i in items),gsc_clicks=clicks,gsc_impressions=impressions,gsc_ctr=Decimal(clicks)/Decimal(impressions) if impressions else None,ga4_sessions=ga4[0] if ga4 else None,ga4_engagement_rate=ga4[1] if ga4 else None,inlinks=crawl.inlink_count if crawl else None,depth=crawl.depth if crawl else None,technical_issues=len(crawl.issues) if crawl else None,score=max(i.score.total for i in items)))
  return CompetitorGapReport(target_domain=target,competitors=tuple(sorted(competitors,key=lambda x:(-x.top_10_appearances,x.average_observed_position,x.domain))),keyword_gaps=tuple(sorted(gaps,key=lambda x:(-x.score.total,x.keyword))),page_gaps=tuple(sorted(page_gaps,key=lambda x:(-x.score,x.target_page))),competitor_pages=tuple(sorted(pages,key=lambda x:(-x.top_10_appearances,x.best_observed_rank,x.url))),trends=tuple(trends),notes=("Observed coverage is limited to persisted Nexora tracked keywords and is not organic market share.","GSC average position and tracked SERP position use different measurement contexts."))
