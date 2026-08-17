"""Deterministic local interpretation layered over fetched website HTML."""
from __future__ import annotations
import json,re
from collections.abc import Awaitable,Callable
from bs4 import BeautifulSoup
from src.core.enums import Priority
from src.core.exceptions import CrawlError,RepositoryError
from src.local_seo.domain import Citation,LocalBusiness,LocalIssue,LocalSEOAudit
from src.local_seo.dto import LocalSEOAuditRequest,LocalSEOAuditResponse
from src.local_seo.repository import LocalSEORepository
def norm(value:str)->str:
 value=value.lower()
 value=re.sub(r"\b(street|st\.)\b","st",value)
 value=re.sub(r"\b(road|rd\.)\b","rd",value)
 return re.sub(r"[^a-z0-9]","",value)
class LocalSEOAuditService:
 def __init__(self,fetch_html:Callable[[str],Awaitable[str]],repository:LocalSEORepository)->None:self._fetch,self._repo=fetch_html,repository
 async def audit(self,request:LocalSEOAuditRequest)->LocalSEOAuditResponse:
  try:
   html=await self._fetch(str(request.business.website)); audit=self.analyze(request.business,html,request.citations); await self._repo.save(audit); return LocalSEOAuditResponse(success=True,audit=audit,message="Local SEO audit completed.")
  except CrawlError as exc:return LocalSEOAuditResponse(success=False,errors=[str(exc)],message="Website could not be fetched.")
  except RepositoryError as exc:return LocalSEOAuditResponse(success=False,errors=[str(exc)],message="Local SEO audit could not be saved.")
 def analyze(self,business:LocalBusiness,html:str,citations:list[Citation])->LocalSEOAudit:
  soup=BeautifulSoup(html or "","lxml"); text=soup.get_text(" ",strip=True); issues:list[LocalIssue]=[]
  def add(code,category,severity,evidence,recommendation):issues.append(LocalIssue(code=code,category=category,severity=severity,title=code.replace('_',' ').title(),description="Deterministic local website signal is missing or inconsistent.",evidence=evidence,recommendation=recommendation))
  name,address,phone,city=business.name,business.location.address,business.phone,business.location.city
  if name and norm(name) not in norm(text):add("business_name_missing","website_signals",Priority.HIGH,"Business name absent from visible website text.","Show the business name on key local pages.")
  if address and norm(address) not in norm(text):add("address_missing","website_signals",Priority.MEDIUM,"Address absent from visible website text.","Publish a consistent address on the contact or location page.")
  if phone and norm(phone) not in norm(text):add("phone_missing","website_signals",Priority.MEDIUM,"Phone absent from visible website text.","Publish a consistent local phone number.")
  if city and norm(city) not in norm(text):add("city_missing","website_signals",Priority.LOW,"City absent from visible website text.","Add natural city/location context where relevant.")
  schemas=[]; malformed=False
  for script in soup.find_all("script",attrs={"type":re.compile("application/ld\\+json",re.I)}):
   try:
    payload=json.loads(script.string or script.get_text()); values=payload if isinstance(payload,list) else [payload]; schemas += [str(v.get("@type","")) for v in values if isinstance(v,dict)]
   except (TypeError,ValueError):malformed=True
  if not any(value.lower() in {"localbusiness","organization"} for value in schemas):add("local_schema_missing","structured_data",Priority.MEDIUM,"No LocalBusiness or Organization JSON-LD found.","Add accurate JSON-LD based on verified business data.")
  if malformed:add("local_schema_malformed","structured_data",Priority.MEDIUM,"Malformed JSON-LD block.","Fix structured-data JSON syntax.")
  consistency=self._citations(business,citations)
  scores={"website_signals":100.0,"structured_data":100.0}
  for issue in issues:scores[issue.category]=max(0,scores[issue.category]-(15 if issue.severity is Priority.HIGH else 8 if issue.severity is Priority.MEDIUM else 3))
  if citations:scores["citations"]=100.0 if consistency=="consistent" else 70.0 if consistency=="partially_consistent" else 40.0
  signals={"business_name_present":norm(name) in norm(text),"address_present":not address or norm(address) in norm(text),"phone_present":not phone or norm(phone) in norm(text),"city_present":not city or norm(city) in norm(text),"schema_types":", ".join(sorted(set(schemas))),"citation_consistency":consistency,"reviews":"unavailable","gbp":"unavailable","local_rank":"unavailable"}
  return LocalSEOAudit(business=business,overall_score=round(sum(scores.values())/len(scores),2),category_scores=scores,issues=issues,signals=signals,citations=citations)
 def _citations(self,business:LocalBusiness,citations:list[Citation])->str:
  if not citations:return "unknown"
  fields=[(business.name,lambda c:c.business_name),(business.location.address,lambda c:c.address),(business.phone,lambda c:c.phone)]
  matches=0;total=0
  for citation in citations:
   for canonical,getter in fields:
    if canonical: total+=1; matches+=norm(canonical)==norm(getter(citation))
  return "consistent" if matches==total else "partially_consistent" if matches else "inconsistent"
