"""Offline Analytics HTTP parity and provider-safety tests."""
import asyncio,tempfile,unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from api.config import APISettings
from api.main import create_app
from src.ga4.domain import GA4Dimension,GA4Property,GA4Record,GA4Snapshot,ReportingPeriod as GA4Period
from src.ga4.repository import GA4Repository
from src.search_console.domain import ReportingPeriod,SearchConsoleProperty,SearchDimension,SearchPerformanceRecord,SearchPerformanceSnapshot
from src.search_console.repository import SearchConsoleRepository

class AnalyticsAPITests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/"analytics.db";self.client=TestClient(create_app(APISettings(database_path=self.path,allowed_origins=("http://localhost:3000",))))
  period=ReportingPeriod(start_date=date(2026,8,1),end_date=date(2026,8,15));prop=SearchConsoleProperty(site_url="https://example.com",permission_level="owner");repo=SearchConsoleRepository(self.path)
  async def seed():
   await repo.save(SearchPerformanceSnapshot(property=prop,period=period,records=(SearchPerformanceRecord(clicks=15,impressions=150,ctr=Decimal(".1"),average_position=Decimal("4")),)))
   for d,keys in ((SearchDimension.QUERY,("alpha","beta")),(SearchDimension.PAGE,("https://example.com/a","https://example.com/b")),(SearchDimension.DATE,("2026-08-01","2026-08-02"))):
    records=tuple(SearchPerformanceRecord(dimensions=(d,),keys=(key,),clicks=10-i*5,impressions=100-i*50,ctr=Decimal(".1"),average_position=Decimal(3+i)) for i,key in enumerate(keys));await repo.save(SearchPerformanceSnapshot(property=prop,period=period,dimensions=(d,),records=records))
   ga=GA4Repository(self.path);gp=GA4Property(property_id="123",display_name="Example");gperiod=GA4Period(start_date=period.start_date,end_date=period.end_date)
   metrics={"activeUsers":Decimal(80),"sessions":Decimal(100),"screenPageViews":Decimal(130),"engagementRate":Decimal(".7"),"keyEvents":Decimal(4)}
   await ga.save(GA4Snapshot(property=gp,period=gperiod,metrics=tuple(metrics),records=(GA4Record(metrics=metrics),)))
   for d,keys in ((GA4Dimension.DATE,("20260801","20260802")),(GA4Dimension.LANDING_PAGE,("/a","/b")),(GA4Dimension.CHANNEL,("Organic Search","Direct")),(GA4Dimension.EVENT,("page_view","signup"))):
    await ga.save(GA4Snapshot(property=gp,period=gperiod,dimensions=(d,),metrics=tuple(metrics),records=tuple(GA4Record(dimensions=(d,),keys=(key,),metrics={**metrics,"sessions":Decimal(100-i*50)}) for i,key in enumerate(keys))))
  asyncio.run(seed())
 def tearDown(self):self.client.close();self.temp.cleanup()
 def test_summary_resources_keep_sources_separate(self):
  data=self.client.get("/api/v1/analytics").json();self.assertEqual(data["gsc_resources"]["summary"]["source"],"GOOGLE_SEARCH_CONSOLE");self.assertEqual(data["ga4_resources"]["summary"][0]["source"],"GOOGLE_ANALYTICS_4");self.assertNotIn("sessions",data["gsc_resources"]["summary"]);self.assertNotIn("clicks",data["ga4_resources"]["summary"][0])
 def test_filters_sorting_pagination_and_dates(self):
  result=self.client.get("/api/v1/analytics/gsc/queries?query=alpha&sort_by=impressions&limit=1").json();self.assertEqual(result["total"],1);self.assertFalse(result["has_more"]);self.assertEqual(result["items"][0]["query"],"alpha")
  pages=self.client.get("/api/v1/analytics/ga4/pages?sort_by=sessions&limit=1").json();self.assertEqual(pages["total"],2);self.assertTrue(pages["has_more"])
  self.assertEqual(self.client.get("/api/v1/analytics/gsc/queries?start_date=2026-08-15&end_date=2026-08-01").status_code,422)
  self.assertEqual(self.client.get("/api/v1/analytics/ga4/pages?sort_by=clicks").status_code,422)
 def test_exports_and_all_gets_make_zero_provider_calls(self):
  with patch("src.search_console.providers.google_provider.GoogleSearchConsoleProvider.query_search_analytics") as gsc,patch("src.ga4.providers.RealGA4Provider.run_report") as ga4:
   for path in ("/api/v1/analytics","/api/v1/analytics/gsc/queries?query=a","/api/v1/analytics/gsc/pages?sort_by=page","/api/v1/analytics/ga4/pages?limit=1","/api/v1/analytics/exports/gsc-queries"):
    self.assertEqual(self.client.get(path).status_code,200,path)
   gsc.assert_not_called();ga4.assert_not_called()
 def test_refresh_is_explicitly_provider_gated_and_filtered_exports_are_reads(self):
  self.assertEqual(self.client.post("/api/v1/analytics/refresh/gsc",json={"property":"https://example.com","start_date":"2026-08-01","end_date":"2026-08-15"}).status_code,409)
  self.assertEqual(self.client.post("/api/v1/analytics/refresh/ga4",json={"property_id":"123","start_date":"2026-08-01","end_date":"2026-08-15"}).status_code,409)
  export=self.client.get("/api/v1/analytics/exports/gsc-queries?value=alpha&start_date=2026-08-01&end_date=2026-08-15&sort_by=impressions")
  self.assertEqual(export.status_code,200);self.assertIn("alpha",export.text);self.assertNotIn("beta",export.text)
 def test_comparison_and_host_validated_cross_source_page_evidence(self):
  self.assertEqual(self.client.get("/api/v1/analytics/comparison/gsc").json()["status"],"HISTORY_UNAVAILABLE")
  result=self.client.get("/api/v1/analytics/cross-source/pages").json();self.assertEqual(result["total"],2);self.assertEqual(result["items"][0]["attribution"],"NOT_INFERRED");self.assertEqual(result["items"][0]["search_evidence"]["source"],"GOOGLE_SEARCH_CONSOLE");self.assertEqual(result["items"][0]["behavior_evidence"]["source"],"GOOGLE_ANALYTICS_4")
