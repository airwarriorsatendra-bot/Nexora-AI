"""Explicit Local SEO composition with isolated, replaceable providers."""
from __future__ import annotations
import inspect,os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from dotenv import load_dotenv
from src.core.constants import ENV_DATABASE_URL
from src.local_seo.domain import LocalSEOIntelligence
from src.local_seo.providers import GoogleBusinessProfileProvider, OfflineBusinessProfileProvider, OfflineCitationProvider, OfflineLocalCompetitorProvider, OfflineLocalRankProvider, OfflineReviewProvider
from src.local_seo.repository import LocalSEORepository
from src.local_seo.service import LocalSEOAuditService
from src.research.services.crawler_service import CrawlerService

@dataclass(frozen=True,slots=True)
class LocalSEOSettings:
 database_path:Path;gbp_client_id:str="";gbp_client_secret:str="";gbp_refresh_token:str="";gbp_account_id:str="";gbp_location_id:str=""
 @classmethod
 def from_environment(cls,environment:dict[str,str]|None=None):
  if environment is None:load_dotenv();environment=dict(os.environ)
  value=environment.get(ENV_DATABASE_URL,"");path=Path(value.removeprefix("sqlite:///")) if value.startswith("sqlite:///") else Path(value) if value else Path(__file__).resolve().parents[2]/"storage"/"backlinks.db"
  return cls(path,*(environment.get(x,"").strip() for x in ("GBP_CLIENT_ID","GBP_CLIENT_SECRET","GBP_REFRESH_TOKEN","GBP_ACCOUNT_ID","GBP_LOCATION_ID")))
 @property
 def gbp_configured(self)->bool:return all((self.gbp_client_id,self.gbp_client_secret,self.gbp_refresh_token))

@dataclass(slots=True)
class LocalSEOApplication:
 service:LocalSEOAuditService;repository:LocalSEORepository;business_profile:object;reviews:object;ranks:object;citations:object;competitors:object;_closed:bool=False
 async def audit(self,request):return await self.service.audit(request)
 async def refresh_business_profile(self):
  return await self.service.persist_business_profile(await self.business_profile.refresh_selected())
 async def snapshot(self):
  locations=tuple(await self.repository.list_locations());nap=tuple(await self.repository.list_nap_evidence());reviews=tuple(await self.repository.list_reviews());ranks=tuple(await self.repository.list_ranks());targets=tuple(await self.repository.list_targets());citations=self.service.citation_states(targets,await self.repository.list_citations());competitors=tuple(await self.repository.list_competitors());queries=tuple(await self.repository.list_queries());pages=tuple(await self.repository.list_landing_pages());history=tuple(await self.repository.list_history());summaries=tuple(self.service.summarize_reviews(x.location_id,[r for r in reviews if r.location_id==x.location_id]) for x in locations);nap_assessments=tuple(self.service.nap(x.location_id,[e for e in nap if e.location_id==x.location_id]) for x in locations);comparisons=self.service.compare_ranks(ranks);opportunities=self.service.opportunities(naps=nap_assessments,reviews=summaries,ranks=comparisons,citations=citations,pages=pages)
  return LocalSEOIntelligence(locations=locations,nap_evidence=nap,nap_assessments=nap_assessments,reviews=reviews,review_summaries=summaries,ranks=comparisons,queries=queries,landing_pages=pages,citations=citations,citation_targets=targets,competitors=competitors,opportunities=opportunities,history=history)
 async def aclose(self):
  if self._closed:return
  self._closed=True
  for item in (self.competitors,self.citations,self.ranks,self.reviews,self.business_profile):
   close=getattr(item,"aclose",None)
   if close:
    result=close()
    if inspect.isawaitable(result):await result

class LocalSEOComposition:
 def __init__(self,settings:LocalSEOSettings,*,crawler_factory=CrawlerService,repository_factory=LocalSEORepository,business_profile_factory:Callable[[],object]|None=None,review_factory=OfflineReviewProvider,rank_factory=OfflineLocalRankProvider,citation_factory=OfflineCitationProvider,competitor_factory=OfflineLocalCompetitorProvider):self.s=settings;self.crawler_factory=crawler_factory;self.repository_factory=repository_factory;self.business_profile_factory=business_profile_factory;self.factories=(review_factory,rank_factory,citation_factory,competitor_factory)
 def _business_profile(self):
  if self.business_profile_factory:return self.business_profile_factory()
  if self.s.gbp_configured:return GoogleBusinessProfileProvider(self.s.gbp_client_id,self.s.gbp_client_secret,self.s.gbp_refresh_token,self.s.gbp_account_id,self.s.gbp_location_id)
  return OfflineBusinessProfileProvider()
 def build(self):
  repo=self.repository_factory(self.s.database_path);crawler=self.crawler_factory();service=LocalSEOAuditService(crawler.fetch_html,repo);providers=[factory() for factory in self.factories];return LocalSEOApplication(service,repo,self._business_profile(),*providers)
