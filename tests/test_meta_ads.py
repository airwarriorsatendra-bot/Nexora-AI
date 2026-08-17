import tempfile,unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from src.meta_ads.domain import MetaAccount,MetaCampaign,Period
from src.meta_ads.dto import MetaAdsAuditRequest
from src.meta_ads.repository import MetaAdsRepository
from src.meta_ads.service import MetaAdsAnalysisService
class MetaAdsTests(unittest.IsolatedAsyncioTestCase):
 async def test_metrics_frequency_zero_and_persistence(self):
  t=tempfile.TemporaryDirectory();r=MetaAdsRepository(Path(t.name)/'m.db');c=MetaCampaign(campaign_id='1',name='A',impressions=300000,reach=50000,clicks=1000,spend=Decimal('5000'),conversions=0,conversion_value=0);q=MetaAdsAuditRequest(account=MetaAccount(ad_account_id='a',currency='INR'),period=Period(date_from=date(2026,8,1),date_to=date(2026,8,15)),campaigns=[c]);x=await MetaAdsAnalysisService(r).analyze(q);self.assertEqual(c.frequency,Decimal('6'));self.assertIsNone(c.cpa);self.assertEqual(x.audit.source,'IMPORT');self.assertEqual(len(x.audit.recommendations),2);self.assertEqual(len(await r.list_recent()),1);t.cleanup()
