from __future__ import annotations
import os
from dotenv import load_dotenv
from src.competitor_gap.composition import CompetitorGapComposition,CompetitorGapSettings
class CompetitorGapDashboardWorkflow:
 def __init__(self,factory=None):self.factory=factory or self._build
 @staticmethod
 def _build():load_dotenv();return CompetitorGapComposition(CompetitorGapSettings.from_environment(dict(os.environ))).build()
 async def targets(self):
  app=self.factory()
  try:return await app.targets()
  finally:await app.aclose()
 async def load(self,target):
  app=self.factory()
  try:return await app.analyze(target)
  finally:await app.aclose()
