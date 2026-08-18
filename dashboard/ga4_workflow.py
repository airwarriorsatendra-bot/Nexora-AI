"""Presentation adapter for explicit, read-only GA4 refreshes."""
from __future__ import annotations
import os
from collections.abc import Callable
from dotenv import load_dotenv
from src.ga4.composition import GA4Application,GA4Composition,GA4Settings
from src.ga4.domain import GA4Property,ReportingPeriod
from src.ga4.dto import GA4ReportRequest
class GA4DashboardWorkflow:
 def __init__(self,factory:Callable[[],GA4Application]|None=None):self._factory=factory or self._build;self._custom=factory is not None
 def configured(self):
  settings=GA4Settings.from_environment();return self._custom or bool(settings.property_id and settings.client_id and settings.client_secret and settings.refresh_token)
 async def properties(self):
  app=self._factory()
  try:
   values=await app.service.list_properties()
   return values or ((GA4Property(property_id=app.provider.c[0] if False else GA4Settings.from_environment().property_id,display_name='Configured GA4 property'),) if GA4Settings.from_environment().property_id else ())
  finally:await app.aclose()
 async def refresh(self,property,period):
  app=self._factory()
  try:return await app.service.refresh_standard_views(GA4ReportRequest(property=property,period=period))
  finally:await app.aclose()
 @staticmethod
 def _build():load_dotenv();return GA4Composition(GA4Settings.from_environment(dict(os.environ))).build()
