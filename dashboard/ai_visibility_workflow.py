from __future__ import annotations
import os
from dotenv import load_dotenv
from src.ai_visibility.composition import AIVisibilityComposition,AIVisibilitySettings
class AIVisibilityDashboardWorkflow:
 def __init__(self,factory=None):self.factory=factory or self._build
 @staticmethod
 def _build():load_dotenv();return AIVisibilityComposition(AIVisibilitySettings.from_environment(dict(os.environ))).build()
 async def providers(self):
  app=self.factory()
  try:return [p.capability for p in app.providers]
  finally:await app.aclose()
 async def prompts(self):
  app=self.factory()
  try:return await app.prompts()
  finally:await app.aclose()
 async def candidates(self):
  app=self.factory()
  try:return await app.candidates()
  finally:await app.aclose()
 async def add_prompt(self,text):
  app=self.factory()
  try:return await app.add_prompt(text)
  finally:await app.aclose()
 async def run(self,requests,repetitions,providers):
  app=self.factory()
  try:return await app.run(requests,repetitions,providers)
  finally:await app.aclose()
 async def history(self):
  app=self.factory()
  try:return await app.history()
  finally:await app.aclose()
