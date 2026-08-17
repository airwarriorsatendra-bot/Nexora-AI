"""Dashboard workflow for imported Google Ads analysis."""
from __future__ import annotations
import pandas as pd
from src.google_ads.composition import GoogleAdsComposition,GoogleAdsSettings
from src.google_ads.dto import GoogleAdsAuditRequest
class GoogleAdsDashboardWorkflow:
 def __init__(self,factory=None):self._factory=factory or (lambda:GoogleAdsComposition(GoogleAdsSettings.from_environment()).build())
 async def execute(self,account,period,campaigns):return await self._factory().analyze(GoogleAdsAuditRequest(account=account,period=period,campaigns=campaigns))
def campaigns_to_dataframe(audit):return pd.DataFrame([{**c.model_dump(mode='json'),'ctr':str(c.ctr) if c.ctr is not None else None,'cpa':str(c.cpa) if c.cpa is not None else None,'roas':str(c.roas) if c.roas is not None else None} for c in audit.campaigns])
