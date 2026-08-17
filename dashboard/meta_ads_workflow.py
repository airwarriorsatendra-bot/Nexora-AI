import pandas as pd
from src.meta_ads.composition import MetaAdsComposition,MetaAdsSettings
from src.meta_ads.dto import MetaAdsAuditRequest
class MetaAdsDashboardWorkflow:
 def __init__(self,factory=None):self.f=factory or(lambda:MetaAdsComposition(MetaAdsSettings.from_environment()).build())
 async def execute(self,a,p,c):return await self.f().analyze(MetaAdsAuditRequest(account=a,period=p,campaigns=c))
def campaigns_to_dataframe(a):return pd.DataFrame([{**x.model_dump(mode='json'),'ctr':str(x.ctr),'cpc':str(x.cpc),'cpm':str(x.cpm),'cpa':str(x.cpa),'roas':str(x.roas),'frequency':str(x.frequency)}for x in a.campaigns])
