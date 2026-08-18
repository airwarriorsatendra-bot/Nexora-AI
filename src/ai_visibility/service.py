from __future__ import annotations
import re
from collections import defaultdict
from urllib.parse import urlsplit
from uuid import uuid4
import httpx
from src.ai_visibility.domain import *
from src.core.exceptions import ExternalAPIError
class AIVisibilityService:
 @staticmethod
 def category(text):
  q=text.casefold();return PromptCategory.BRANDED if q.startswith(("tell me about","what is")) else PromptCategory.QUESTION_AEO if re.match(r"^(who|what|when|where|why|how|which|can|does|is|are|should)\b",q) else PromptCategory.COMPARISON if re.search(r"\b(vs|versus|compare|comparison)\b",q) else PromptCategory.COMMERCIAL_INVESTIGATION if re.search(r"\b(best|top|review)\b",q) else PromptCategory.PRODUCT_SERVICE_DISCOVERY if re.search(r"\b(where|buy|find)\b",q) else PromptCategory.CUSTOM
 @staticmethod
 def generated_prompts(query,max_variants=3):
  q=" ".join(query.split()).rstrip("?");items=(q if q[:1].isupper() else q.capitalize(),f"What are some options for {q}?",f"Which providers or brands should I consider for {q}?");return tuple(dict.fromkeys(items))[:max(1,min(3,max_variants))]
 @staticmethod
 def _match(text,name,aliases,order_names):
  matches=[]
  for alias in dict.fromkeys((name,)+tuple(aliases)):
   pattern=r"(?<![\w])"+re.escape(alias)+r"(?![\w])";found=list(re.finditer(pattern,text,re.I))
   if found:matches.append((found[0].start(),alias,len(found)))
  if not matches:return None
  offset,alias,count=min(matches);ordered=sorted((pos,n) for n,(pos,_,_) in order_names.items());order=1+sum(pos<offset for pos,_ in ordered);return Mention(name=name,matched_alias=alias,count=count,first_offset=offset,mention_order=order,excerpt=text[max(0,offset-50):offset+len(alias)+50])
 async def observe(self,run_id,request,provider):
  try:
   response=await provider.run_visibility_prompt(request.prompt)
   if not response.response_text.strip():return self._failure(run_id,request,provider,ObservationState.EMPTY_RESPONSE)
  except httpx.TimeoutException:return self._failure(run_id,request,provider,ObservationState.TIMEOUT)
  except httpx.HTTPStatusError as exc:return self._failure(run_id,request,provider,ObservationState.RATE_LIMITED if exc.response.status_code==429 else ObservationState.PROVIDER_ERROR)
  except Exception:return self._failure(run_id,request,provider,ObservationState.PROVIDER_ERROR)
  names={request.brand_name:(-1,"",0)};competitor_matches=[]
  for name,aliases in request.competitors.items():
   match=self._match(response.response_text,name,aliases,{})
   if match:names[name]=(match.first_offset,match.matched_alias,match.count);competitor_matches.append(match)
  brand=self._match(response.response_text,request.brand_name,request.brand_aliases,names)
  ordered=sorted(([brand] if brand else [])+competitor_matches,key=lambda item:item.first_offset)
  order_by_name={item.name:index+1 for index,item in enumerate(ordered)}
  if brand:brand=brand.model_copy(update={"mention_order":order_by_name[brand.name]})
  competitor_matches=[item.model_copy(update={"mention_order":order_by_name[item.name]}) for item in competitor_matches]
  citations=[]
  target=self._host(request.target_domain)
  for item in response.citations:
   host=self._host(item.url);competitor=next((name for name,aliases in request.competitors.items() if host in {self._host(x) for x in aliases if "." in x}),None);citations.append(CitationObservation(url=item.url,domain=host,title=item.title,index=item.index,is_target=host==target or host.endswith("."+target),competitor=competitor))
  available=response.classification==ProviderClassification.GROUNDED_WITH_CITATIONS
  return AIVisibilityObservation(run_id=run_id,prompt_id=request.prompt.prompt_id,prompt=request.prompt.text,category=request.prompt.category,provider=response.provider,model=response.model,classification=response.classification,state=ObservationState.SUCCESS,response_text=response.response_text,brand_mention=brand,competitor_mentions=tuple(sorted(competitor_matches,key=lambda x:x.first_offset)),citations=tuple(citations),citation_tracking_available=available,target_domain_cited=any(x.is_target for x in citations) if available else None,observed_at=response.observed_at)
 def _failure(self,run_id,request,provider,state):return AIVisibilityObservation(run_id=run_id,prompt_id=request.prompt.prompt_id,prompt=request.prompt.text,category=request.prompt.category,provider=provider.capability.provider,model=provider.capability.model,classification=provider.capability.classification,state=state,citation_tracking_available=provider.capability.citations_supported,target_domain_cited=None,error_category=state.value)
 def report(self,run):
  success=[o for o in run.observations if o.state==ObservationState.SUCCESS];mention=sum(o.brand_mention is not None for o in success);capable=[o for o in success if o.citation_tracking_available];groups=defaultdict(list)
  for o in success:groups[(o.provider,o.model)].append(o)
  summaries=[]
  for (provider,model),items in groups.items():
   citation=[o for o in items if o.citation_tracking_available];summaries.append(ProviderSummary(provider=provider,model=model,successful_observations=len(items),brand_mention_coverage=sum(o.brand_mention is not None for o in items)/len(items),citation_coverage=sum(bool(o.target_domain_cited) for o in citation)/len(citation) if citation else None,citation_denominator=len(citation),competitor_mentions=sum(len(o.competitor_mentions) for o in items),mention_stability=sum(o.brand_mention is not None for o in items)/len(items),sample_size=len(items)))
  actions=[]
  if any(not o.brand_mention and o.competitor_mentions for o in success):actions.append("Target absent while configured competitors were observed; review differentiation, entity clarity, answer structure, and source support.")
  if any(o.brand_mention and o.target_domain_cited is False for o in capable):actions.append("A brand mention was observed without a target-domain citation; source citation was not observed in those responses.")
  return VisibilityReport(run=run,provider_summaries=tuple(summaries),brand_mention_coverage=mention/len(success) if success else 0,citation_coverage=sum(bool(o.target_domain_cited) for o in capable)/len(capable) if capable else None,citation_denominator=len(capable),competitors_observed=len({m.name for o in success for m in o.competitor_mentions}),target_domain_citations=sum(bool(o.target_domain_cited) for o in capable),actions=tuple(actions),limitations=("AI responses are nondeterministic and provider/model specific; observations do not represent universal AI rankings.","Ungrounded model responses support mention monitoring but not structured citation tracking.","Provider failures are excluded from visibility denominators."))
 def changes(self,current,previous):
  prior={(o.prompt_id,o.provider,o.model):o for o in previous if o.state==ObservationState.SUCCESS};result=[]
  for item in current:
   if item.state!=ObservationState.SUCCESS:continue
   old=prior.get((item.prompt_id,item.provider,item.model));visible=item.brand_mention is not None;cited=bool(item.target_domain_cited)
   if old is None:state=VisibilityChange.NEWLY_VISIBLE if visible else VisibilityChange.NOT_OBSERVED
   elif visible and old.brand_mention:state=VisibilityChange.CONSISTENTLY_VISIBLE
   elif visible:state=VisibilityChange.NEWLY_VISIBLE
   elif old.brand_mention:state=VisibilityChange.LOST_VISIBILITY
   else:state=VisibilityChange.NOT_OBSERVED
   if old is not None and cited and not old.target_domain_cited:state=VisibilityChange.NEW_CITATION
   elif old is not None and old.target_domain_cited and not cited:state=VisibilityChange.LOST_CITATION
   result.append((item,state))
  return tuple(result)
 @staticmethod
 def _host(value):return (urlsplit(value if "://" in value else "//"+value).hostname or "").casefold().removeprefix("www.")
