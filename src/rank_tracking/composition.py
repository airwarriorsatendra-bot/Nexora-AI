"""Explicit composition and lifecycle ownership for rank tracking."""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from src.core.constants import ENV_DATABASE_URL,ENV_SERPER_API_KEY
from src.rank_tracking.providers import OfflineSERPProvider
from src.rank_tracking.repository import RankTrackingRepository
from src.rank_tracking.serper_provider import SerperRankProvider
from src.rank_tracking.service import RankTrackingService
@dataclass(frozen=True,slots=True)
class RankTrackingSettings:
 database_path:Path;serper_api_key:str="";offline:bool=False
 @classmethod
 def from_environment(cls,environment=None):
  v=environment if environment is not None else os.environ;db=v.get(ENV_DATABASE_URL,"");path=Path(db.removeprefix("sqlite:///")) if db.startswith("sqlite:///") else Path(db) if db else Path(__file__).resolve().parents[2]/"storage"/"backlinks.db";return cls(path,v.get(ENV_SERPER_API_KEY,"").strip())
 @property
 def configured(self):return self.offline or bool(self.serper_api_key)
@dataclass(slots=True)
class RankTrackingApplication:
 settings:RankTrackingSettings;provider:object;repository:RankTrackingRepository;service:RankTrackingService;closed:bool=False
 async def aclose(self):
  if not self.closed:await self.provider.aclose();self.closed=True
class RankTrackingComposition:
 def __init__(self,settings,provider_factory=None,repository_factory=RankTrackingRepository):self.settings,self.provider_factory,self.repository_factory=settings,provider_factory,repository_factory
 def build(self):
  provider=self.provider_factory(self.settings) if self.provider_factory else OfflineSERPProvider() if self.settings.offline or not self.settings.serper_api_key else SerperRankProvider(self.settings.serper_api_key);repo=self.repository_factory(self.settings.database_path);return RankTrackingApplication(self.settings,provider,repo,RankTrackingService(provider,repo))
