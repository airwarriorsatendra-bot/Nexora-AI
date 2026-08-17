"""Explicit composition for offline/import Google Ads analysis."""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv
from src.core.constants import ENV_DATABASE_URL
from src.google_ads.repository import GoogleAdsRepository
from src.google_ads.service import GoogleAdsAnalysisService
@dataclass(frozen=True,slots=True)
class GoogleAdsSettings:
 database_path:Path
 @classmethod
 def from_environment(cls,environment=None):
  if environment is None:load_dotenv();environment=dict(os.environ)
  v=environment.get(ENV_DATABASE_URL,"");return cls(Path(v.removeprefix('sqlite:///')) if v.startswith('sqlite:///') else Path(v) if v else Path(__file__).resolve().parents[2]/'storage'/'backlinks.db')
class GoogleAdsComposition:
 def __init__(self,settings,*,repository_factory=GoogleAdsRepository):self._settings,self._factory=settings,repository_factory
 def build(self):return GoogleAdsAnalysisService(self._factory(self._settings.database_path))
