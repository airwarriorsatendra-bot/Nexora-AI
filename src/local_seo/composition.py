"""Explicit Local SEO composition using the shared crawler."""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv
from src.core.constants import ENV_DATABASE_URL
from src.research.services.crawler_service import CrawlerService
from src.local_seo.repository import LocalSEORepository
from src.local_seo.service import LocalSEOAuditService
@dataclass(frozen=True,slots=True)
class LocalSEOSettings:
 database_path:Path
 @classmethod
 def from_environment(cls,environment:dict[str,str]|None=None):
  if environment is None:load_dotenv();environment=dict(os.environ)
  value=environment.get(ENV_DATABASE_URL,"")
  return cls(Path(value.removeprefix("sqlite:///")) if value.startswith("sqlite:///") else Path(value) if value else Path(__file__).resolve().parents[2]/"storage"/"backlinks.db")
class LocalSEOComposition:
 def __init__(self,settings:LocalSEOSettings,*,crawler_factory=CrawlerService,repository_factory=LocalSEORepository):self._settings,self._crawler_factory,self._repository_factory=settings,crawler_factory,repository_factory
 def build(self):
  crawler=self._crawler_factory();return LocalSEOAuditService(crawler.fetch_html,self._repository_factory(self._settings.database_path))
