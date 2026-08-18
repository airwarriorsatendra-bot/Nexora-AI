from __future__ import annotations
import os
from dotenv import load_dotenv
from src.competitor_gap.composition import CompetitorGapSettings
from src.content_intelligence.composition import ContentIntelligenceComposition
class ContentIntelligenceDashboardWorkflow:
 def __init__(self,factory=None):self.factory=factory or self._build
 @staticmethod
 def _build():load_dotenv();return ContentIntelligenceComposition(CompetitorGapSettings.from_environment(dict(os.environ))).build()
 async def targets(self):
  app=self.factory()
  try:return await app.targets()
  finally:await app.aclose()
 async def generate(self,target,keyword):
  app=self.factory()
  try:return await app.generate(target,keyword)
  finally:await app.aclose()
