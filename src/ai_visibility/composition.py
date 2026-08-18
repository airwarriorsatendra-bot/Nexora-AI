from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from src.core.constants import *
from src.ai_visibility.providers import OfflineVisibilityProvider,TextGenerationVisibilityAdapter
from src.ai_visibility.repository import AIVisibilityRepository
from src.ai_visibility.service import AIVisibilityService
from src.ai_visibility.domain import AIVisibilityRun,VisibilityRequest
from src.research.providers.openai_provider import OpenAIProvider
from src.research.providers.gemini_provider import GeminiProvider
from src.research.providers.claude_provider import ClaudeProvider
from src.research.providers.groq_provider import GroqProvider
from src.research.providers.nvidia_provider import NvidiaProvider
from src.competitor_gap.composition import CompetitorGapApplication,CompetitorGapSettings
@dataclass(frozen=True,slots=True)
class AIVisibilitySettings:
 database_path:Path;provider:str="";api_key:str="";model:str="";max_prompts:int=50;max_providers:int=5;max_repetitions:int=3
 @classmethod
 def from_environment(cls,environment=None):
  e=environment if environment is not None else os.environ;raw=e.get(ENV_DATABASE_URL,"");db=Path(raw.removeprefix("sqlite:///")) if raw.startswith("sqlite:///") else Path(raw) if raw else Path(__file__).resolve().parents[2]/"storage"/"backlinks.db";p=e.get(ENV_AI_PROVIDER,"").lower();keys={"openai":ENV_OPENAI_API_KEY,"gemini":ENV_GEMINI_API_KEY,"groq":ENV_GROQ_API_KEY,"claude":ENV_CLAUDE_API_KEY,"nvidia":ENV_NVIDIA_API_KEY};models={"openai":e.get("OPENAI_MODEL","gpt-4.1-mini"),"gemini":e.get("GEMINI_MODEL","gemini-2.0-flash"),"groq":e.get("GROQ_MODEL","llama-3.3-70b-versatile"),"claude":e.get("CLAUDE_MODEL","claude-3-5-haiku-latest"),"nvidia":e.get(ENV_NVIDIA_MODEL,"meta/llama-3.3-70b-instruct")};return cls(db,p,e.get(keys.get(p,""),"").strip(),models.get(p,""))
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
    source="AEO_QUESTION_OPPORTUNITY" if self.service.category(gap.keyword).value=="QUESTION_AEO" else "COMPETITOR_GAP" if gap.competitors_ahead else "RANK_TRACKED_KEYWORD"
    candidates.append((source,target,gap.keyword,gap.mapped_page))
  return tuple(dict.fromkeys(candidates))[:50]
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
  if not s.provider or not s.api_key:return []
  builders={"openai":lambda:OpenAIProvider(s.api_key,s.model),"gemini":lambda:GeminiProvider(s.api_key,s.model),"groq":lambda:GroqProvider(s.api_key,s.model),"claude":lambda:ClaudeProvider(s.api_key,s.model),"nvidia":lambda:NvidiaProvider(s.api_key,s.model)}
  return [TextGenerationVisibilityAdapter(builders[s.provider](),s.provider,s.model)] if s.provider in builders else []
