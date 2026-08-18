"""Observed-rank service with honest matching, changes, and competitors."""
from __future__ import annotations
from collections import defaultdict
from datetime import UTC,datetime
from decimal import Decimal
from urllib.parse import urlsplit,urlunsplit
from src.rank_tracking.domain import CompetitorObservation,RankChange,RankChangeType,RankCheck,TrackedKeyword
class RankTrackingService:
 MAX_CHECKS_PER_RUN=50
 def __init__(self,provider,repository):self.provider,self.repository=provider,repository
 @staticmethod
 def _host(value):
  host=urlsplit(value if "://" in value else "//"+value).hostname or "";return host.lower().removeprefix("www.")
 @staticmethod
 def _url(value):
  p=urlsplit(value);return (RankTrackingService._host(value),p.path.rstrip("/") or "/")
 def matches(self,k,r):return self._url(r.url)==self._url(k.target_url) if k.target_url else self._host(r.domain or r.url)==k.target_domain
 match=matches
 @staticmethod
 def change(previous,current,has_previous=True):
  if not has_previous:return RankChange(change_type=RankChangeType.BASELINE,current_position=current)
  if previous is None and current is not None:return RankChange(change_type=RankChangeType.NEWLY_RANKING,current_position=current)
  if previous is not None and current is None:return RankChange(change_type=RankChangeType.LOST,previous_position=previous)
  if previous is None:return RankChange(change_type=RankChangeType.STABLE)
  movement=previous-current;kind=RankChangeType.IMPROVED if movement>0 else RankChangeType.DECLINED if movement<0 else RankChangeType.STABLE
  return RankChange(change_type=kind,previous_position=previous,current_position=current,movement=movement)
 async def add_keyword(self,item):return await self.repository.save_keyword(item)
 async def check(self,keyword,depth=20):
  previous=await self.repository.latest(keyword.keyword_id,keyword.context);results=await self.provider.search(keyword.keyword,keyword.context,depth);position=next((r.position for r in results if self.matches(keyword,r)),None);check=RankCheck(keyword_id=keyword.keyword_id,keyword=keyword.keyword,context=keyword.context,depth=depth,provider=self.provider.provider_name,results=results,target_position=position);await self.repository.save_check(check);return check,self.change(previous.target_position if previous else None,position,previous is not None)
 async def check_active(self,depth=20,limit=MAX_CHECKS_PER_RUN):
  keywords=(await self.repository.list_keywords(active_only=True))[:max(1,min(limit,self.MAX_CHECKS_PER_RUN))];return [await self.check(k,depth) for k in keywords]
 async def current_rows(self):
  keywords={k.keyword_id:k for k in await self.repository.list_keywords()};out=[]
  for c in await self.repository.latest_checks():
   h=await self.repository.history(c.keyword_id,c.context);p=h[-2].target_position if len(h)>1 else None;ch=self.change(p,c.target_position,len(h)>1);k=keywords.get(c.keyword_id);out.append((k,c,ch))
  return out
 async def competitors(self):
  checks=await self.repository.latest_checks();targets={k.keyword_id:k.target_domain for k in await self.repository.list_keywords()};data=defaultdict(lambda:{"keywords":set(),"positions":[]})
  for c in checks:
   for r in c.results:
    d=self._host(r.domain or r.url)
    if d and d!=targets.get(c.keyword_id):data[d]["keywords"].add(c.keyword);data[d]["positions"].append(r.position)
  return tuple(sorted((CompetitorObservation(domain=d,keywords_observed=len(v["keywords"]),top_3_appearances=sum(p<=3 for p in v["positions"]),top_10_appearances=sum(p<=10 for p in v["positions"]),average_observed_position=Decimal(sum(v["positions"]))/Decimal(len(v["positions"])),best_observed_position=min(v["positions"])) for d,v in data.items()),key=lambda x:(-x.top_10_appearances,x.average_observed_position,x.domain)))
