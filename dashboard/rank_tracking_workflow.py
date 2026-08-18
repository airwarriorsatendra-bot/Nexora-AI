"""Streamlit adapter for explicit rank tracking actions."""
from __future__ import annotations
import os
from collections.abc import Callable
from dotenv import load_dotenv
from src.rank_tracking.composition import RankTrackingApplication,RankTrackingComposition,RankTrackingSettings
from src.rank_tracking.domain import Device,TrackedKeyword,TrackingContext
class RankTrackingDashboardWorkflow:
 def __init__(self,factory:Callable[[],RankTrackingApplication]|None=None):self.factory=factory or self._build;self.custom=factory is not None
 def configured(self):
  if self.custom:return True
  load_dotenv();return RankTrackingSettings.from_environment(dict(os.environ)).configured
 async def add(self,keyword,target_domain,target_url,country,device,gsc=None):
  app=self.factory()
  try:
   item=TrackedKeyword(keyword=keyword,target_domain=target_domain,target_url=target_url or None,context=TrackingContext(country=country,device=Device(device)),gsc_average_position=getattr(gsc,"average_position",None),gsc_clicks=getattr(gsc,"clicks",None),gsc_impressions=getattr(gsc,"impressions",None));return await app.service.add_keyword(item)
  finally:await app.aclose()
 async def check(self,depth):
  app=self.factory()
  try:return await app.service.check_active(depth)
  finally:await app.aclose()
 async def snapshot(self):
  app=self.factory()
  try:
   return {"keywords":await app.repository.list_keywords(),"rows":await app.service.current_rows(),"competitors":await app.service.competitors()}
  finally:await app.aclose()
 async def history(self,keyword):
  app=self.factory()
  try:return await app.repository.history(keyword.keyword_id,keyword.context)
  finally:await app.aclose()
 @staticmethod
 def _build():
  load_dotenv();return RankTrackingComposition(RankTrackingSettings.from_environment(dict(os.environ))).build()
