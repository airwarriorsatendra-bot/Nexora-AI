"""Offline imported-data Google Ads analysis tests."""
from __future__ import annotations
import tempfile,unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from dashboard.google_ads_workflow import GoogleAdsDashboardWorkflow,campaigns_to_dataframe
from src.google_ads.domain import GoogleAdsAccount,GoogleAdsCampaign,ReportingPeriod
from src.google_ads.dto import GoogleAdsAuditRequest
from src.google_ads.repository import GoogleAdsRepository
from src.google_ads.service import GoogleAdsAnalysisService
class GoogleAdsTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):self.tmp=tempfile.TemporaryDirectory();self.repo=GoogleAdsRepository(Path(self.tmp.name)/'ads.db');self.account=GoogleAdsAccount(customer_id='123',currency_code='INR');self.period=ReportingPeriod(date_from=date(2026,8,1),date_to=date(2026,8,15))
 async def asyncTearDown(self):self.tmp.cleanup()
 async def test_metrics_zero_safety_recommendations_persistence_and_provenance(self):
  a=GoogleAdsCampaign(campaign_id='a',name='A',impressions=100000,clicks=5000,cost=Decimal('10000'),conversions=Decimal('100'),conversion_value=Decimal('50000'));b=GoogleAdsCampaign(campaign_id='b',name='B',impressions=1000,clicks=1000,cost=Decimal('5000'),conversions=Decimal(),conversion_value=Decimal())
  response=await GoogleAdsAnalysisService(self.repo).analyze(GoogleAdsAuditRequest(account=self.account,period=self.period,campaigns=[a,b]));self.assertTrue(response.success);audit=response.audit;assert audit;self.assertEqual(a.ctr,Decimal('0.05'));self.assertEqual(a.average_cpc,Decimal('2'));self.assertEqual(a.cpa,Decimal('100'));self.assertEqual(a.roas,Decimal('5'));self.assertIsNone(b.cpa);self.assertEqual(audit.source,'IMPORT');self.assertTrue(audit.recommendations);self.assertEqual(len(await self.repo.list_recent()),1);self.assertIn('ctr',campaigns_to_dataframe(audit).columns)
 def test_invalid_period_and_nonnegative_metrics(self):
  with self.assertRaises(ValueError):ReportingPeriod(date_from=date(2026,2,2),date_to=date(2026,2,1))
  with self.assertRaises(ValueError):GoogleAdsCampaign(campaign_id='x',name='x',impressions=-1,clicks=0,cost=0,conversions=0,conversion_value=0)
 async def test_idempotent_snapshot_and_workflow(self):
  campaign=GoogleAdsCampaign(campaign_id='x',name='X',impressions=0,clicks=0,cost=0,conversions=0,conversion_value=0);service=GoogleAdsAnalysisService(self.repo);workflow=GoogleAdsDashboardWorkflow(factory=lambda:service);await workflow.execute(self.account,self.period,[campaign]);await workflow.execute(self.account,self.period,[campaign]);self.assertEqual(len(await self.repo.list_recent()),1)
