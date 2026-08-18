from __future__ import annotations
from dataclasses import dataclass
from src.competitor_gap.composition import CompetitorGapApplication,CompetitorGapSettings
from src.content_intelligence.service import ContentIntelligenceService
class ContentIntelligenceApplication:
 def __init__(self,settings,service=None):self.settings=settings;self.service=service or ContentIntelligenceService();self.gaps=CompetitorGapApplication(CompetitorGapSettings(settings.database_path))
 async def targets(self):
  result=[]
  for target in await self.gaps.targets():
   report=await self.gaps.analyze(target);result.extend((target,g.keyword,g.mapped_page) for g in report.keyword_gaps)
  return result
 async def generate(self,target,keyword):
  report=await self.gaps.analyze(target);gap=next(g for g in report.keyword_gaps if g.keyword==keyword);history=await self.gaps.crawls.history();compatible=[c for c in history if self.gaps.service.host(str(c.request.start_url))==self.gaps.service.host(target)];crawl=compatible[-1] if compatible else None;pages={p.normalized_url:p for p in crawl.pages} if crawl else {};return self.service.generate(gap,report.keyword_gaps,pages.get(gap.mapped_page),crawl.links if crawl else ())
 async def aclose(self):await self.gaps.aclose()
class ContentIntelligenceComposition:
 def __init__(self,settings,service_factory=ContentIntelligenceService):self.settings=settings;self.service_factory=service_factory
 def build(self):return ContentIntelligenceApplication(self.settings,self.service_factory())
