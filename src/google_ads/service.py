"""Deterministic Google Ads analysis from imported or test-fixture campaigns."""
from __future__ import annotations
from decimal import Decimal
from src.core.enums import Priority
from src.google_ads.domain import GoogleAdsAudit,GoogleAdsRecommendation
from src.google_ads.dto import GoogleAdsAuditRequest,GoogleAdsAuditResponse
from src.google_ads.repository import GoogleAdsRepository
class GoogleAdsAnalysisService:
 def __init__(self,repository:GoogleAdsRepository,*,min_clicks:int=100,high_spend:Decimal=Decimal('1000')):self._repo,self._min_clicks,self._high_spend=repository,min_clicks,high_spend
 async def analyze(self,request:GoogleAdsAuditRequest)->GoogleAdsAuditResponse:
  recommendations=[];total_cost=sum((c.cost for c in request.campaigns),Decimal()) ; total_conversions=sum((c.conversions for c in request.campaigns),Decimal()); account_cpa=(total_cost/total_conversions) if total_conversions else None
  for c in request.campaigns:
   if c.clicks<self._min_clicks:continue
   if c.cost>=self._high_spend and not c.conversions:recommendations.append(GoogleAdsRecommendation(campaign_id=c.campaign_id,category='waste',severity=Priority.HIGH,title='Spend with zero conversions',evidence=f'Cost {c.cost} {request.account.currency_code}; conversions {c.conversions}.',suggested_action='Review targeting, search terms, and conversion tracking before increasing spend.',confidence=Decimal('0.9')))
   elif account_cpa is not None and c.cpa is not None and c.cpa>account_cpa:recommendations.append(GoogleAdsRecommendation(campaign_id=c.campaign_id,category='efficiency',severity=Priority.MEDIUM,title='CPA above account average',evidence=f'Campaign CPA {c.cpa}; account CPA {account_cpa}.',suggested_action='Review bids, targeting, and conversion quality.',confidence=Decimal('0.75')))
  audit=GoogleAdsAudit(account=request.account,period=request.period,source=request.source,campaigns=request.campaigns,recommendations=recommendations);await self._repo.save(audit);return GoogleAdsAuditResponse(success=True,audit=audit,message='Google Ads imported-data analysis completed.')
