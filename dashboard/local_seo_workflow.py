"""Dashboard adapter for Local SEO source-layer audits."""
from __future__ import annotations
import os
from collections.abc import Callable
import pandas as pd
from src.local_seo.composition import LocalSEOComposition,LocalSEOSettings
from src.local_seo.dto import LocalSEOAuditRequest
from src.local_seo.service import LocalSEOAuditService
class LocalSEODashboardWorkflow:
 def __init__(self,factory:Callable[[],LocalSEOAuditService]|None=None):self._factory=factory or (lambda:LocalSEOComposition(LocalSEOSettings.from_environment()).build())
 async def execute(self,business,citations=[]):return await self._factory().audit(LocalSEOAuditRequest(business=business,citations=citations))
def issues_to_dataframe(audit):
 return pd.DataFrame([issue.model_dump(mode="json") for issue in audit.issues],columns=["code","category","severity","title","description","evidence","recommendation","source"])
