"""Composition loader for derived-only competitor gap intelligence."""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin,urlsplit
from src.core.constants import ENV_DATABASE_URL
from src.competitor_gap.service import CompetitorGapService
from src.ga4.domain import GA4Dimension
from src.ga4.repository import GA4Repository
from src.rank_tracking.repository import RankTrackingRepository
from src.search_console.domain import SearchDimension
from src.search_console.repository import SearchConsoleRepository
from src.site_crawl.repository import SiteCrawlRepository
from src.site_crawl.crawler import normalize_url
@dataclass(frozen=True,slots=True)
class CompetitorGapSettings:
 database_path:Path
 @classmethod
 def from_environment(cls,environment=None):
  v=environment if environment is not None else os.environ;raw=v.get(ENV_DATABASE_URL,"");return cls(Path(raw.removeprefix("sqlite:///")) if raw.startswith("sqlite:///") else Path(raw) if raw else Path(__file__).resolve().parents[2]/"storage"/"backlinks.db")
class CompetitorGapApplication:
 def __init__(self,settings,service=None):self.settings=settings;self.service=service or CompetitorGapService();self.rank=RankTrackingRepository(settings.database_path);self.gsc=SearchConsoleRepository(settings.database_path);self.ga4=GA4Repository(settings.database_path);self.crawls=SiteCrawlRepository(settings.database_path)
 async def targets(self):return sorted({k.target_domain for k in await self.rank.list_keywords()})
 async def analyze(self,target):
  keywords=[k for k in await self.rank.list_keywords() if self.service.host(k.target_domain)==self.service.host(target)];checks=[c for c in await self.rank.latest_checks() if any(k.keyword_id==c.keyword_id for k in keywords)];histories={k.keyword_id:tuple(await self.rank.history(k.keyword_id,k.context)) for k in keywords}
  query=await self.gsc.latest(dimensions=(SearchDimension.QUERY,));gsc={}
  if query:
   for r in query.records:
    q=r.dimension_value(SearchDimension.QUERY)
    if q:gsc[q]=(r.impressions,r.clicks,r.average_position,r.ctr)
  base=f"https://{self.service.host(target)}/";ga4={};snapshot=await self.ga4.latest((GA4Dimension.LANDING_PAGE,))
  if snapshot:
   for r in snapshot.records:
    if r.keys:
     try:ga4[normalize_url(urljoin(base,r.keys[0]))]=(r.metrics.get("sessions",0),r.metrics.get("engagementRate"))
     except Exception:pass
  crawl_pages={};history=await self.crawls.history()
  compatible=[c for c in history if (urlsplit(str(c.request.start_url)).hostname or "").lower().removeprefix("www.")==self.service.host(target)]
  if compatible:crawl_pages={p.normalized_url:p for p in compatible[-1].pages}
  return self.service.analyze(target,keywords,checks,histories,gsc,ga4,crawl_pages)
 async def aclose(self):return None
class CompetitorGapComposition:
 def __init__(self,settings,service_factory=CompetitorGapService):self.settings=settings;self.service_factory=service_factory
 def build(self):return CompetitorGapApplication(self.settings,self.service_factory())

