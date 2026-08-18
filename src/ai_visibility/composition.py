from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from src.core.constants import *
from src.ai_visibility.providers import OfflineVisibilityProvider,TextGenerationVisibilityAdapter
from src.ai_visibility.grounded_providers import GeminiGroundedProvider,PerplexitySonarGroundedProvider,OpenAIGroundedProvider,ClaudeGroundedProvider
from src.ai_visibility.repository import AIVisibilityRepository
from src.ai_visibility.service import AIVisibilityService
from src.ai_visibility.domain import AIVisibilityRun,VisibilityRequest
from src.ai_visibility.citation_intelligence import CitationIntelligenceService
from src.research.providers.openai_provider import OpenAIProvider
from src.research.providers.gemini_provider import GeminiProvider
from src.research.providers.claude_provider import ClaudeProvider
from src.research.providers.groq_provider import GroqProvider
from src.research.providers.nvidia_provider import NvidiaProvider
from src.competitor_gap.composition import CompetitorGapApplication,CompetitorGapSettings
@dataclass(frozen=True,slots=True)
class AIVisibilitySettings:
 database_path:Path;provider:str="";api_key:str="";model:str="";max_prompts:int=25;max_providers:int=3;max_repetitions:int=3;grounded_provider:str="";grounded_api_key:str="";grounded_model:str=""
 @classmethod
 def from_environment(cls,environment=None):
  e=environment if environment is not None else os.environ;raw=e.get(ENV_DATABASE_URL,"");db=Path(raw.removeprefix("sqlite:///")) if raw.startswith("sqlite:///") else Path(raw) if raw else Path(__file__).resolve().parents[2]/"storage"/"backlinks.db";p=e.get(ENV_AI_PROVIDER,"").lower();keys={"openai":ENV_OPENAI_API_KEY,"gemini":ENV_GEMINI_API_KEY,"groq":ENV_GROQ_API_KEY,"claude":ENV_CLAUDE_API_KEY,"nvidia":ENV_NVIDIA_API_KEY};models={"openai":e.get("OPENAI_MODEL","gpt-4.1-mini"),"gemini":e.get("GEMINI_MODEL","gemini-2.0-flash"),"groq":e.get("GROQ_MODEL","openai/gpt-oss-120b"),"claude":e.get("CLAUDE_MODEL","claude-3-5-haiku-latest"),"nvidia":e.get(ENV_NVIDIA_MODEL,"meta/llama-3.3-70b-instruct")};gp=e.get(ENV_GROUNDED_AI_PROVIDER,"").strip().lower();gkeys={"gemini":ENV_GEMINI_API_KEY,"perplexity":ENV_PERPLEXITY_API_KEY,"openai":ENV_OPENAI_API_KEY,"claude":ENV_CLAUDE_API_KEY};defaults={"gemini":"gemini-2.5-flash","perplexity":"sonar","openai":"gpt-4.1-mini","claude":"claude-sonnet-4-5"};gm=e.get(ENV_GROUNDED_AI_MODEL,defaults.get(gp,"")).strip();return cls(db,p,e.get(keys.get(p,""),"").strip(),models.get(p,""),grounded_provider=gp,grounded_api_key=e.get(gkeys.get(gp,""),"").strip(),grounded_model=gm)
class AIVisibilityApplication:
 def __init__(self,settings,service,repository,providers):self.settings=settings;self.service=service;self.repository=repository;self.providers=providers;self.evidence=CompetitorGapApplication(CompetitorGapSettings(settings.database_path))
 async def add_prompt(self,text,category=None,source="MANUAL",context=""):
  from src.ai_visibility.domain import MonitoredPrompt
  return await self.repository.save_prompt(MonitoredPrompt(text=" ".join(text.split()),category=category or self.service.category(text),source=source,context=context))
 async def prompts(self):return await self.repository.list_prompts()
 async def candidates(self):
  candidates=[]
  for target in await self.evidence.targets():
   report=await self.evidence.analyze(target)
   for gap in report.keyword_gaps[:50]:
    category=self.service.category(gap.keyword)
    if gap.gsc_impressions is not None and gap.gsc_impressions>0:candidates.append(("GSC_HIGH_IMPRESSION",target,gap.keyword,gap.mapped_page))
    if category.value=="QUESTION_AEO":candidates.append(("AEO_QUESTION_OPPORTUNITY",target,gap.keyword,gap.mapped_page))
    if category.value=="COMMERCIAL_INVESTIGATION":candidates.append(("GSC_COMMERCIAL_QUERY",target,gap.keyword,gap.mapped_page))
    if gap.target_position is not None:candidates.append(("RANK_TRACKED_KEYWORD",target,gap.keyword,gap.mapped_page))
    if gap.competitors_ahead:candidates.append(("COMPETITOR_GAP",target,gap.keyword,gap.mapped_page))
    candidates.append(("CONTENT_PRIMARY_QUERY",target,gap.keyword,gap.mapped_page))
  return tuple(dict.fromkeys(candidates))[:50]
 async def promote_candidates(self,candidates,limit=25):
  promoted=[]
  for source,target,query,page in tuple(candidates)[:max(1,min(25,limit))]:promoted.append(await self.add_prompt(query,source=source,context=f"target={target};page={page or ''}"))
  return tuple(promoted)
 async def page_intelligence(self,target):
  from src.aeo_geo.service import AEOGEOService
  from src.content_intelligence.service import ContentIntelligenceService
  report=await self.evidence.analyze(target);host=self.evidence.service.host(target);history=await self.evidence.crawls.history(limit=500);compatible=[c for c in history if self.evidence.service.host(str(c.request.start_url))==host];crawl=compatible[-1] if compatible else None;pages={p.normalized_url:p for p in crawl.pages} if crawl else {};readiness=AEOGEOService().analyze(target,report,pages);briefs=[]
  for gap in report.keyword_gaps:
   if gap.mapped_page:briefs.append(ContentIntelligenceService().generate(gap,report.keyword_gaps,pages.get(gap.mapped_page),crawl.links if crawl else ()))
  observations=await self.history();return CitationIntelligenceService().enrich_pages(observations,host,readiness_pages=readiness.pages,page_gaps=report.page_gaps,keyword_gaps=report.keyword_gaps,crawl_pages=crawl.pages if crawl else (),briefs=briefs)
 async def citation_gap_brief(self,target,keyword,observation):
  from src.content_intelligence.service import ContentIntelligenceService
  report=await self.evidence.analyze(target);gap=next(g for g in report.keyword_gaps if g.keyword==keyword);history=await self.evidence.crawls.history(limit=500);host=self.evidence.service.host(target);compatible_crawls=[c for c in history if self.evidence.service.host(str(c.request.start_url))==host];crawl=compatible_crawls[-1] if compatible_crawls else None;pages={p.normalized_url:p for p in crawl.pages} if crawl else {};brief=ContentIntelligenceService().generate(gap,report.keyword_gaps,pages.get(gap.mapped_page),crawl.links if crawl else ());observations=[o for o in await self.history() if o.prompt==observation.prompt and o.provider==observation.provider and o.model==observation.model];evidence=CitationIntelligenceService().gap_evidence(observation,observations);return CitationIntelligenceService.attach_to_brief(brief,evidence)
 async def history(self):return await self.repository.history()
 async def run(self,requests,repetitions=1,provider_names=None):
  selected=[p for p in self.providers if not provider_names or p.capability.provider in provider_names][:self.settings.max_providers];requests=tuple(requests)[:self.settings.max_prompts];repetitions=max(1,min(self.settings.max_repetitions,repetitions))
  if not requests:raise ValueError("At least one monitoring prompt is required.")
  if not selected:raise ValueError("At least one configured visibility provider is required.")
  run=AIVisibilityRun(brand_name=requests[0].brand_name,target_domain=requests[0].target_domain,providers=tuple(p.capability.provider for p in selected),prompt_count=len(requests),repetitions=repetitions);await self.repository.save_run(run);observations=[]
  for request in requests:
   await self.repository.save_prompt(request.prompt)
   for provider in selected:
    for _ in range(repetitions):observations.append(await self.service.observe(run.run_id,request,provider))
  run=run.model_copy(update={"observations":tuple(observations)});await self.repository.save_run(run);return self.service.report(run)
 async def aclose(self):
  for provider in self.providers:await provider.aclose()
  await self.evidence.aclose()
class AIVisibilityComposition:
 def __init__(self,settings,providers=None):self.settings=settings;self.injected=providers
 def build(self):return AIVisibilityApplication(self.settings,AIVisibilityService(),AIVisibilityRepository(self.settings.database_path),self.injected if self.injected is not None else self._providers())
 def _providers(self):
  s=self.settings
  builders={"openai":lambda:OpenAIProvider(s.api_key,s.model),"gemini":lambda:GeminiProvider(s.api_key,s.model),"groq":lambda:GroqProvider(s.api_key,s.model),"claude":lambda:ClaudeProvider(s.api_key,s.model),"nvidia":lambda:NvidiaProvider(s.api_key,s.model)}
  providers=[TextGenerationVisibilityAdapter(builders[s.provider](),s.provider,s.model)] if s.provider in builders and s.api_key else []
  if s.grounded_provider=="gemini" and s.grounded_api_key and s.grounded_model:providers.append(GeminiGroundedProvider(s.grounded_api_key,s.grounded_model))
  elif s.grounded_provider=="perplexity" and s.grounded_api_key and s.grounded_model:providers.append(PerplexitySonarGroundedProvider(s.grounded_api_key,s.grounded_model))
  elif s.grounded_provider=="openai" and s.grounded_api_key and s.grounded_model:providers.append(OpenAIGroundedProvider(s.grounded_api_key,s.grounded_model))
  elif s.grounded_provider=="claude" and s.grounded_api_key and s.grounded_model:providers.append(ClaudeGroundedProvider(s.grounded_api_key,s.grounded_model))
  return providers
