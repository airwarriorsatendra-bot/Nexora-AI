"""Explicit constructor composition for Backlink Intelligence 2.0."""
from __future__ import annotations
import inspect,logging,os
from dataclasses import dataclass
from pathlib import Path
from typing import Any,Callable
from dotenv import load_dotenv
from src.backlinks.providers import AuthorityMetricsProvider,MozAuthorityProvider
from src.backlinks.repositories.backlink_repository import BacklinkRepository
from src.backlinks.services.discovery_service import BacklinkDiscoveryService
from src.backlinks.services.intelligence_service import BacklinkIntelligenceService
from src.backlinks.services.verification_service import BacklinkVerificationService
from src.core.constants import ENV_DATABASE_URL,ENV_MOZ_API_TOKEN,ENV_MOZ_AUTHORITY_FRESHNESS_DAYS
from src.core.exceptions import ConfigurationError
from src.research.services.crawler_service import CrawlerService

@dataclass(frozen=True,slots=True)
class BacklinkSettings:
 database_path:Path;moz_api_token:str="";authority_freshness_days:int=30
 @classmethod
 def from_environment(cls,environment:dict[str,str]|None=None):
  if environment is None:load_dotenv();environment=dict(os.environ)
  value=environment.get(ENV_DATABASE_URL,"").strip()
  if value.startswith("sqlite:///"):path=Path(value.removeprefix("sqlite:///"))
  elif value and "://" in value:raise ConfigurationError("Backlink repositories support SQLite DATABASE_URL values only.")
  else:path=Path(value) if value else Path(__file__).resolve().parents[2]/"storage"/"backlinks.db"
  try:freshness=int(environment.get(ENV_MOZ_AUTHORITY_FRESHNESS_DAYS,"30"))
  except ValueError as exc:raise ConfigurationError("MOZ_AUTHORITY_FRESHNESS_DAYS must be an integer.") from exc
  if not 1<=freshness<=365:raise ConfigurationError("MOZ_AUTHORITY_FRESHNESS_DAYS must be between 1 and 365.")
  return cls(path,environment.get(ENV_MOZ_API_TOKEN,"").strip(),freshness)

@dataclass(slots=True)
class BacklinkApplication:
 discovery_service:BacklinkDiscoveryService;verification_service:BacklinkVerificationService;intelligence_service:BacklinkIntelligenceService;repository:BacklinkRepository;authority_provider:AuthorityMetricsProvider|None=None;_closeables:tuple[Any,...]=();_closed:bool=False
 async def aclose(self):
  if self._closed:return
  self._closed=True;seen=set()
  for dependency in reversed(self._closeables):
   if id(dependency) in seen:continue
   seen.add(id(dependency));close=getattr(dependency,"aclose",None) or getattr(dependency,"close",None)
   if callable(close):
    result=close()
    if inspect.isawaitable(result):await result
 async def __aenter__(self):return self
 async def __aexit__(self,exc_type,exc,traceback):await self.aclose()

class BacklinkComposition:
 def __init__(self,settings:BacklinkSettings,*,authority_provider:AuthorityMetricsProvider|None=None,logger:logging.Logger|None=None,crawler_factory:Callable[[],Any]=CrawlerService,repository_factory:Callable[[Path],BacklinkRepository]=BacklinkRepository):self._settings=settings;self._injected_authority=authority_provider;self._logger=logger or logging.getLogger(__name__);self._crawler_factory=crawler_factory;self._repository_factory=repository_factory
 def build(self):
  crawler=self._crawler_factory();repository=self._repository_factory(self._settings.database_path);provider=self._injected_authority or (MozAuthorityProvider(self._settings.moz_api_token,logger=self._logger) if self._settings.moz_api_token else None);intelligence=BacklinkIntelligenceService(repository,provider,freshness_days=self._settings.authority_freshness_days);closeables=tuple(x for x in (crawler,provider,repository) if x is not None);return BacklinkApplication(BacklinkDiscoveryService(repository,self._logger),BacklinkVerificationService(crawler.fetch_html,repository,self._logger),intelligence,repository,provider,closeables)
