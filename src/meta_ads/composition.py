import os
from dataclasses import dataclass
from pathlib import Path
from src.meta_ads.repository import MetaAdsRepository
from src.meta_ads.service import MetaAdsAnalysisService
@dataclass(frozen=True,slots=True)
class MetaAdsSettings:
 database_path:Path
 @classmethod
 def from_environment(cls,e=None):
  e=e or os.environ;v=e.get('DATABASE_URL','');return cls(Path(v.removeprefix('sqlite:///')) if v.startswith('sqlite:///') else Path(v) if v else Path(__file__).resolve().parents[2]/'storage'/'backlinks.db')
class MetaAdsComposition:
 def __init__(self,s,*,repository_factory=MetaAdsRepository):self.s,self.f=s,repository_factory
 def build(self):return MetaAdsAnalysisService(self.f(self.s.database_path))
