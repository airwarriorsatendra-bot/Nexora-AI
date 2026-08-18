import os
from dataclasses import dataclass
from pathlib import Path
from src.core.constants import ENV_DATABASE_URL,ENV_GSC_CLIENT_ID,ENV_GSC_CLIENT_SECRET,ENV_GSC_REFRESH_TOKEN,ENV_GA4_PROPERTY_ID
from src.ga4.providers import RealGA4Provider,OfflineGA4Provider
from src.ga4.repository import GA4Repository
from src.ga4.service import GA4Service
@dataclass(frozen=True,slots=True)
class GA4Settings:
 database_path:Path;client_id:str='';client_secret:str='';refresh_token:str='';property_id:str=''
 @classmethod
 def from_environment(cls,environment=None):
  v=environment or os.environ;db=v.get(ENV_DATABASE_URL,'');path=Path(db.removeprefix('sqlite:///')) if db.startswith('sqlite:///') else Path(db) if db else Path(__file__).resolve().parents[2]/'storage'/'backlinks.db';return cls(path,v.get(ENV_GSC_CLIENT_ID,''),v.get(ENV_GSC_CLIENT_SECRET,''),v.get(ENV_GSC_REFRESH_TOKEN,''),v.get(ENV_GA4_PROPERTY_ID,''))
@dataclass
class GA4Application:
 provider:object;repository:GA4Repository;service:GA4Service;closed:bool=False
 async def aclose(self):
  if not self.closed:await self.provider.aclose();self.closed=True
class GA4Composition:
 def __init__(self,settings,provider_factory=None,repository_factory=GA4Repository):self.s=settings;self.p=provider_factory;self.r=repository_factory
 def build(self):
  provider=self.p(self.s) if self.p else (RealGA4Provider(self.s.client_id,self.s.client_secret,self.s.refresh_token) if all((self.s.client_id,self.s.client_secret,self.s.refresh_token)) else OfflineGA4Provider())
  repo=self.r(self.s.database_path);return GA4Application(provider,repo,GA4Service(provider,repo))
