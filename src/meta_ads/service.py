from decimal import Decimal
from src.core.enums import Priority
from src.meta_ads.domain import MetaAudit,MetaRecommendation
from src.meta_ads.dto import MetaAdsAuditRequest,MetaAdsAuditResponse
class MetaAdsAnalysisService:
 def __init__(self,repo,*,min_clicks=100,high_spend=Decimal('1000'),high_frequency=Decimal('4')):self.r,self.m,self.h,self.f=repo,min_clicks,high_spend,high_frequency
 async def analyze(self,q:MetaAdsAuditRequest):
  rec=[]
  for c in q.campaigns:
   if c.clicks>=self.m and c.spend>=self.h and not c.conversions:rec.append(MetaRecommendation(campaign_id=c.campaign_id,category='waste',severity=Priority.HIGH,title='Spend with zero conversions',evidence=f'Spend {c.spend} {q.account.currency}; conversions {c.conversions}.',suggested_action='Review targeting, creative, and conversion tracking.',confidence=Decimal('.9')))
   if c.frequency is not None and c.frequency>=self.f:rec.append(MetaRecommendation(campaign_id=c.campaign_id,category='frequency',severity=Priority.MEDIUM,title='High frequency observed',evidence=f'Frequency {c.frequency}. No trend data is available to confirm fatigue.',suggested_action='Review creative rotation and audience breadth.',confidence=Decimal('.7')))
  a=MetaAudit(account=q.account,period=q.period,source=q.source,campaigns=q.campaigns,recommendations=rec);await self.r.save(a);return MetaAdsAuditResponse(success=True,audit=a,message='Meta Ads imported-data analysis completed.')
