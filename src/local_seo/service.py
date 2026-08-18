"""Deterministic Local SEO audit and evidence intelligence."""
from __future__ import annotations
import json,re
from collections.abc import Awaitable,Callable,Iterable
from datetime import UTC,datetime
from statistics import median
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from src.core.enums import Priority
from src.core.exceptions import CrawlError,RepositoryError
from src.local_seo.domain import *
from src.local_seo.dto import LocalSEOAuditRequest,LocalSEOAuditResponse
from src.local_seo.repository import LocalSEORepository

def norm(value:str)->str:
 value=value.casefold();value=re.sub(r"\b(street|st\.)\b","st",value);value=re.sub(r"\b(road|rd\.)\b","rd",value);return re.sub(r"[^a-z0-9]","",value)
def normalize_phone(value:str)->str:
 digits=re.sub(r"\D","",value);return ("+"+digits) if digits else ""
class LocalSEOAuditService:
 def __init__(self,fetch_html:Callable[[str],Awaitable[str]],repository:LocalSEORepository)->None:self._fetch,self._repo=fetch_html,repository
 async def audit(self,request:LocalSEOAuditRequest)->LocalSEOAuditResponse:
  try:
   html=await self._fetch(str(request.business.website));audit=self.analyze(request.business,html,request.citations);await self._repo.save(audit);return LocalSEOAuditResponse(success=True,audit=audit,message="Local SEO audit completed.")
  except CrawlError as exc:return LocalSEOAuditResponse(success=False,errors=[str(exc)],message="Website could not be fetched.")
  except RepositoryError as exc:return LocalSEOAuditResponse(success=False,errors=[str(exc)],message="Local SEO audit could not be saved.")
 def analyze(self,business:LocalBusiness,html:str,citations:list[Citation])->LocalSEOAudit:
  soup=BeautifulSoup(html or "","lxml");text=soup.get_text(" ",strip=True);issues=[]
  def add(code,category,severity,evidence,recommendation):issues.append(LocalIssue(code=code,category=category,severity=severity,title=code.replace('_',' ').title(),description="Deterministic local website signal is missing or inconsistent.",evidence=evidence,recommendation=recommendation))
  name,address,phone,city=business.name,business.location.address,business.phone,business.location.city
  if name and norm(name) not in norm(text):add("business_name_missing","website_signals",Priority.HIGH,"Business name absent from visible website text.","Show the business name on key local pages.")
  if address and norm(address) not in norm(text):add("address_missing","website_signals",Priority.MEDIUM,"Address absent from visible website text.","Publish a consistent address on the contact or location page.")
  if phone and norm(phone) not in norm(text):add("phone_missing","website_signals",Priority.MEDIUM,"Phone absent from visible website text.","Publish a consistent local phone number.")
  if city and norm(city) not in norm(text):add("city_missing","website_signals",Priority.LOW,"City absent from visible website text.","Add natural city/location context where relevant.")
  schemas=[];malformed=False
  for script in soup.find_all("script",attrs={"type":re.compile("application/ld\\+json",re.I)}):
   try:
    payload=json.loads(script.string or script.get_text());values=payload if isinstance(payload,list) else [payload];schemas += [str(v.get("@type","")) for v in values if isinstance(v,dict)]
   except (TypeError,ValueError):malformed=True
  if not any(x.casefold() in {"localbusiness","organization"} for x in schemas):add("local_schema_missing","structured_data",Priority.MEDIUM,"No LocalBusiness or Organization JSON-LD found.","Add accurate JSON-LD based on verified business data.")
  if malformed:add("local_schema_malformed","structured_data",Priority.MEDIUM,"Malformed JSON-LD block.","Fix structured-data JSON syntax.")
  consistency=self._citations(business,citations);scores={"website_signals":100.0,"structured_data":100.0}
  for issue in issues:scores[issue.category]=max(0,scores[issue.category]-(15 if issue.severity is Priority.HIGH else 8 if issue.severity is Priority.MEDIUM else 3))
  if citations:scores["citations"]=100.0 if consistency=="consistent" else 70.0 if consistency=="partially_consistent" else 40.0
  signals={"business_name_present":norm(name) in norm(text),"address_present":not address or norm(address) in norm(text),"phone_present":not phone or norm(phone) in norm(text),"city_present":not city or norm(city) in norm(text),"schema_types":", ".join(sorted(set(schemas))),"citation_consistency":consistency,"reviews":"unavailable","gbp":"unavailable","local_rank":"unavailable"}
  return LocalSEOAudit(business=business,overall_score=round(sum(scores.values())/len(scores),2),category_scores=scores,issues=issues,signals=signals,citations=citations)
 def _citations(self,business,citations):
  if not citations:return "unknown"
  fields=[(business.name,lambda c:c.business_name),(business.location.address,lambda c:c.address),(business.phone,lambda c:c.phone)];matches=total=0
  for citation in citations:
   for canonical,getter in fields:
    if canonical:total+=1;matches+=norm(canonical)==norm(getter(citation))
  return "consistent" if matches==total else "partially_consistent" if matches else "inconsistent"
 @staticmethod
 def nap(location_id:str,evidence:Iterable[NAPEvidence])->NAPAssessment:
  items=list(evidence)
  if len(items)<2:return NAPAssessment(location_id=location_id,state=NAPState.INSUFFICIENT_EVIDENCE,evidence_count=len(items),comparable_fields=0,explanation="At least two comparable sources are required.")
  normalized=[]
  for x in items:normalized.append((norm(x.name or "") or None,norm(x.address or "") or None,normalize_phone(x.phone or "") or None))
  mismatches=[];comparable=0
  for index,label in enumerate(("NAME","ADDRESS","PHONE")):
   values={x[index] for x in normalized if x[index]};comparable+=len(values)>0
   if len(values)>1:mismatches.append(label)
  state=NAPState.INSUFFICIENT_EVIDENCE if comparable==0 else NAPState.CONSISTENT if not mismatches else NAPState.MULTIPLE_MISMATCHES if len(mismatches)>1 else getattr(NAPState,mismatches[0]+"_MISMATCH")
  return NAPAssessment(location_id=location_id,state=state,evidence_count=len(items),comparable_fields=comparable,explanation="Evidence comparison only: "+(", ".join(mismatches)+" differ." if mismatches else "comparable fields agree."))
 @staticmethod
 def summarize_reviews(location_id:str,reviews:Iterable[LocalReview],as_of:datetime|None=None)->ReviewSummary:
  current=as_of or datetime.now(UTC);items=list({x.review_id:x for x in reviews}.values());dated=[x for x in items if x.reviewed_at];ages=[max(0,(current-x.reviewed_at.astimezone(UTC)).days) for x in dated];responses=[x for x in items if x.owner_response]
  response_hours=[max(0,(x.owner_response_at-x.reviewed_at).total_seconds()/3600) for x in responses if x.reviewed_at and x.owner_response_at]
  latest=min(ages) if ages else None;state=ReviewActivityState.INSUFFICIENT_EVIDENCE if not ages else ReviewActivityState.ACTIVE if latest<=30 else ReviewActivityState.SLOW if latest<=90 else ReviewActivityState.STALE
  count=len(items);return ReviewSummary(location_id=location_id,average_rating=round(sum(x.rating for x in items)/count,2) if count else None,review_count=count,reviews_30d=sum(x<=30 for x in ages),reviews_90d=sum(x<=90 for x in ages),reviews_365d=sum(x<=365 for x in ages),response_count=len(responses),response_rate=len(responses)/count if count else None,unanswered=count-len(responses),velocity_30d=sum(x<=30 for x in ages)/30 if ages else None,velocity_90d=sum(x<=90 for x in ages)/90 if ages else None,latest_review_age_days=latest,median_review_age_days=median(ages) if ages else None,median_response_hours=median(response_hours) if response_hours else None,activity_state=state)
 @staticmethod
 def compare_ranks(observations:Iterable[LocalRankObservation])->tuple[LocalRankComparison,...]:
  groups={}
  for x in observations:groups.setdefault((x.location_id,x.query.casefold(),x.location_descriptor.casefold(),x.device.casefold(),x.engine.casefold(),x.result_type),[]).append(x)
  output=[]
  for values in groups.values():
   values.sort(key=lambda x:x.observed_at);current=values[-1];previous=values[-2] if len(values)>1 else None
   if previous is None:change=LocalRankChange.NEW if current.position else LocalRankChange.INSUFFICIENT_HISTORY
   elif previous.position is None and current.position is not None:change=LocalRankChange.REAPPEARED
   elif previous.position is not None and current.position is None:change=LocalRankChange.LOST
   elif previous.position==current.position:change=LocalRankChange.UNCHANGED
   elif current.position is not None and previous.position is not None:change=LocalRankChange.IMPROVED if current.position<previous.position else LocalRankChange.DECLINED
   else:change=LocalRankChange.INSUFFICIENT_HISTORY
   movement=(previous.position-current.position) if previous and previous.position and current.position else None;output.append(LocalRankComparison(current=current,previous_position=previous.position if previous else None,change=change,movement=movement))
  return tuple(sorted(output,key=lambda x:(x.current.location_id,x.current.query)))
 @staticmethod
 def local_queries(records,location_terms:Iterable[str],ranks=())->tuple[LocalQueryEvidence,...]:
  terms=tuple(x.casefold().strip() for x in location_terms if x.strip());rank_map={x.current.query.casefold():x for x in ranks};output=[]
  for row in records:
   query=(row.keys[0] if row.keys else "");local_term=next((x for x in terms if x in query.casefold()),"near me" if "near me" in query.casefold() else None)
   if not local_term:continue
   tracked=rank_map.get(query.casefold());opportunity="High-impression local query review" if row.impressions>=100 and float(row.ctr)<0.03 else None
   output.append(LocalQueryEvidence(query=query,location_modifier=local_term,gsc_clicks=row.clicks,gsc_impressions=row.impressions,gsc_ctr=float(row.ctr),gsc_average_position=float(row.average_position),tracked_position=tracked.current.position if tracked else None,tracked_result_type=tracked.current.result_type if tracked else None,opportunity=opportunity))
  return tuple(output)
 @staticmethod
 def citation_states(targets:Iterable[CitationTarget],citations:Iterable[LocalCitation])->tuple[LocalCitation,...]:
  found={(x.location_id,x.directory.casefold()):x for x in citations};return tuple(found.get((t.location_id,t.directory.casefold())) or LocalCitation(location_id=t.location_id,directory=t.directory,state=CitationState.MISSING,source="CONFIGURED_TARGET_UNIVERSE",provider="MANUAL") for t in targets)
 @staticmethod
 def landing_pages(crawl_pages,target_host:str,location_terms:Iterable[str])->tuple[LocalLandingPage,...]:
  host=target_host.casefold().removeprefix("www.");terms=tuple(x.casefold() for x in location_terms if x);output=[]
  for page in crawl_pages:
   page_host=(urlparse(page.normalized_url).hostname or "").casefold().removeprefix("www.")
   if page_host!=host:continue
   haystack=" ".join((page.normalized_url,page.title," ".join(page.h1s))).casefold()
   if not any(term in haystack for term in terms):continue
   technical=page.status_code is None or page.status_code>=400 or page.indexability.value=="NON_INDEXABLE";state=LocalPageState.TECHNICAL_BLOCKER if technical else LocalPageState.WEAK_CONTENT if page.word_count<200 else LocalPageState.LOW_INTERNAL_LINK_SUPPORT if page.inlink_count<2 else LocalPageState.HEALTHY
   output.append(LocalLandingPage(url=page.normalized_url,http_status=page.status_code,indexable=None if page.indexability.value=="UNKNOWN" else page.indexability.value=="INDEXABLE",canonical=page.canonical,title=page.title,h1=page.h1s[0] if page.h1s else "",schema_types=page.structured_data_types,word_count=page.word_count,crawl_depth=page.depth,internal_links=page.inlink_count,state=state,provenance=("SITE_CRAWL",)))
  return tuple(output)
 @staticmethod
 def opportunities(naps=(),reviews=(),ranks=(),citations=(),pages=())->tuple[LocalOpportunity,...]:
  out=[]
  for x in naps:
   if x.state not in {NAPState.CONSISTENT,NAPState.INSUFFICIENT_EVIDENCE}:out.append(LocalOpportunity(opportunity_type="NAP_INCONSISTENCY",location_id=x.location_id,priority=Priority.HIGH,score=85,title="NAP evidence differs",evidence=x.explanation,reason="Comparable source values differ.",recommended_action="Review and correct the verified source records.",provenance=("NAP_EVIDENCE",)))
  for x in reviews:
   if x.unanswered:out.append(LocalOpportunity(opportunity_type="REVIEW_RESPONSE_GAP",location_id=x.location_id,priority=Priority.MEDIUM,score=min(80,40+x.unanswered),title="Observed reviews lack owner responses",evidence=f"{x.unanswered} observed review(s) have no owner response.",reason="Provider-observed response coverage is incomplete.",recommended_action="Review unanswered feedback; any reply remains a separate explicit action.",provenance=("REVIEW_PROVIDER",)))
  for x in ranks:
   if x.change is LocalRankChange.DECLINED:out.append(LocalOpportunity(opportunity_type="LOCAL_RANK_DECLINE",location_id=x.current.location_id,priority=Priority.MEDIUM,score=65,title="Observed local rank declined",evidence=f"{x.current.query}: {x.previous_position} to {x.current.position} ({x.current.result_type.value}).",reason="Compatible observations changed.",recommended_action="Review the query, result type, and supporting page evidence.",provenance=(x.current.provider,)))
  for x in citations:
   if x.state in {CitationState.MISSING,CitationState.PRESENT_INCONSISTENT}:out.append(LocalOpportunity(opportunity_type="CITATION_GAP" if x.state is CitationState.MISSING else "CITATION_INCONSISTENCY",location_id=x.location_id,priority=Priority.MEDIUM,score=60,title=f"Citation evidence: {x.directory}",evidence=x.state.value,reason="Assessment is limited to configured directory targets.",recommended_action="Verify or correct the directory listing.",provenance=(x.source,)))
  for x in pages:
   if x.state is LocalPageState.TECHNICAL_BLOCKER:out.append(LocalOpportunity(opportunity_type="LOCAL_PAGE_TECHNICAL_BLOCKER",location_id=x.location_id,priority=Priority.HIGH,score=90,title="Local page technical blocker",evidence=x.url,reason="Observed crawl evidence blocks normal page availability.",recommended_action="Resolve the observed crawl/indexability issue.",provenance=x.provenance,handoff="Site Crawl"))
  return tuple(out)
