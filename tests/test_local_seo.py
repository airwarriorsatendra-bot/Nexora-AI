"""Offline deterministic Local SEO coverage."""
from __future__ import annotations
import tempfile,unittest
from datetime import UTC,datetime,timedelta
from decimal import Decimal
from pathlib import Path
from streamlit.testing.v1 import AppTest
from dashboard.local_seo import render_local_seo
from dashboard.local_seo_workflow import LocalSEODashboardWorkflow,issues_to_dataframe
from src.local_seo.composition import LocalSEOComposition,LocalSEOSettings
from src.local_seo.domain import BusinessLocation,Citation,CitationState,CitationTarget,LocalBusiness,LocalCitation,LocalRankChange,LocalRankObservation,LocalResultType,LocalReview,NAPEvidence,NAPState,ReviewActivityState
from src.local_seo.dto import LocalSEOAuditRequest
from src.local_seo.repository import LocalSEORepository
from src.local_seo.service import LocalSEOAuditService
from src.local_seo.providers import OfflineBusinessProfileProvider,OfflineCitationProvider,OfflineLocalCompetitorProvider,OfflineLocalRankProvider,OfflineReviewProvider
from src.search_console.domain import SearchDimension,SearchPerformanceRecord
from src.shared.value_objects.location import Location
HTML='''<html><head><title>Acme Dental in Bhopal</title><script type="application/ld+json">{"@type":"LocalBusiness","telephone":"+91 98765 43210"}</script></head><body>Acme Dental 123 Main Street, Bhopal, Madhya Pradesh +91 98765 43210</body></html>'''
def local_page(workflow):
 from dashboard.local_seo import render_local_seo
 render_local_seo(workflow)
class LocalSEOTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):self.tmp=tempfile.TemporaryDirectory();self.repo=LocalSEORepository(Path(self.tmp.name)/"local.db");self.business=LocalBusiness(name="Acme Dental",website="https://acme.example",phone="+91 98765 43210",location=Location(address="123 Main Street, Bhopal, Madhya Pradesh",city="Bhopal",state="Madhya Pradesh"))
 async def asyncTearDown(self):self.tmp.cleanup()
 def service(self,html=HTML):
  async def fetch(url):del url;return html
  return LocalSEOAuditService(fetch,self.repo)
 async def test_nap_schema_citations_persistence_and_export(self):
  citations=[Citation(source="import",business_name="Acme Dental",address="123 Main St. Bhopal Madhya Pradesh",phone="+91-98765-43210")]
  response=await self.service().audit(LocalSEOAuditRequest(business=self.business,citations=citations));self.assertTrue(response.success);audit=response.audit;assert audit
  self.assertEqual(audit.signals["citation_consistency"],"consistent");self.assertIn("LocalBusiness",audit.signals["schema_types"]);self.assertEqual(await self.repo.find("https://acme.example/"),audit);self.assertIn("code",issues_to_dataframe(audit).columns)
 async def test_mismatch_missing_and_unavailable_providers_are_honest(self):
  response=await self.service("<html><script type='application/ld+json'>{bad}</script></html>").audit(LocalSEOAuditRequest(business=self.business,citations=[Citation(source="import",business_name="Other",address="Elsewhere",phone="000")]))
  assert response.audit;codes={i.code for i in response.audit.issues};self.assertIn("business_name_missing",codes);self.assertIn("local_schema_malformed",codes);self.assertEqual(response.audit.signals["citation_consistency"],"inconsistent");self.assertEqual(response.audit.signals["reviews"],"unavailable")
 async def test_idempotence_composition_style_dashboard_workflow(self):
  service=self.service();workflow=LocalSEODashboardWorkflow(factory=lambda:service);first=await workflow.execute(self.business);second=await workflow.execute(self.business);self.assertTrue(first.success and second.success);self.assertEqual(len(await self.repo.list_recent()),1)
 async def test_multi_location_persistence_and_offline_provider_boundaries(self):
  locations=[BusinessLocation(location_id=x,business_id=self.business.business_id,business_name=self.business.name,source="MANUAL") for x in ("one","two")]
  provider=OfflineBusinessProfileProvider(locations);self.assertEqual(len(await provider.locations()),2);self.assertEqual(provider.calls,1)
  for location in locations:await self.repo.save_location(location)
  self.assertEqual({x.location_id for x in await self.repo.list_locations()},{"one","two"})
  for fake in (OfflineReviewProvider(),OfflineLocalRankProvider(),OfflineCitationProvider(),OfflineLocalCompetitorProvider()):self.assertEqual(fake.calls,0)
 async def test_nap_states_and_format_normalization(self):
  base=NAPEvidence(location_id="one",source="GBP",name="Acme Dental",address="123 Main Street",phone="+91 98765 43210")
  same=NAPEvidence(location_id="one",source="WEB",name="ACME DENTAL",address="123 Main St.",phone="+91-98765-43210")
  self.assertEqual(self.service().nap("one",[base,same]).state,NAPState.CONSISTENT)
  changed=same.model_copy(update={"phone":"000","address":"Elsewhere"});self.assertEqual(self.service().nap("one",[base,changed]).state,NAPState.MULTIPLE_MISMATCHES)
  self.assertEqual(self.service().nap("one",[base]).state,NAPState.INSUFFICIENT_EVIDENCE)
 async def test_reviews_rank_history_citations_and_opportunities(self):
  now=datetime(2026,8,18,tzinfo=UTC);reviews=[LocalReview(review_id="r1",location_id="one",rating=5,text="Good service",reviewed_at=now-timedelta(days=5),provider="FAKE"),LocalReview(review_id="r2",location_id="one",rating=3,reviewed_at=now-timedelta(days=100),owner_response="Thanks",owner_response_at=now-timedelta(days=99),provider="FAKE")]
  summary=self.service().summarize_reviews("one",reviews,now);self.assertEqual((summary.review_count,summary.reviews_30d,summary.unanswered),(2,1,1));self.assertEqual(summary.activity_state,ReviewActivityState.ACTIVE)
  old=LocalRankObservation(location_id="one",query="dentist bhopal",location_descriptor="Bhopal",device="mobile",result_type=LocalResultType.LOCAL_PACK,position=3,observed_at=now-timedelta(days=1));new=old.model_copy(update={"observation_id":old.observation_id,"position":7,"observed_at":now});comparison=self.service().compare_ranks([old,new])[0];self.assertEqual(comparison.change,LocalRankChange.DECLINED)
  target=CitationTarget(location_id="one",directory="Configured Directory");citation=self.service().citation_states([target],[])[0];self.assertEqual(citation.state,CitationState.MISSING);self.assertTrue(self.service().opportunities(reviews=[summary],ranks=[comparison],citations=[citation]))
 async def test_gsc_local_query_metrics_remain_separate(self):
  row=SearchPerformanceRecord(dimensions=(SearchDimension.QUERY,),keys=("dentist near me",),clicks=2,impressions=200,ctr=Decimal("0.01"),average_position=Decimal("8.5"));rank=LocalRankObservation(location_id="one",query="dentist near me",location_descriptor="Bhopal",device="mobile",result_type=LocalResultType.MAPS,position=4)
  value=self.service().local_queries([row],["Bhopal"],self.service().compare_ranks([rank]))[0];self.assertEqual(value.gsc_average_position,8.5);self.assertEqual(value.tracked_position,4);self.assertEqual(value.tracked_result_type,LocalResultType.MAPS)
 async def test_dashboard_empty_state_exports_and_zero_provider_calls(self):
  with tempfile.TemporaryDirectory() as directory:
   profile=OfflineBusinessProfileProvider();review=OfflineReviewProvider();rank=OfflineLocalRankProvider();citation=OfflineCitationProvider();competitor=OfflineLocalCompetitorProvider()
   composition=LocalSEOComposition(LocalSEOSettings(Path(directory)/"ui.db"),business_profile_factory=lambda:profile,review_factory=lambda:review,rank_factory=lambda:rank,citation_factory=lambda:citation,competitor_factory=lambda:competitor)
   view=AppTest.from_function(local_page,args=(LocalSEODashboardWorkflow(factory=composition.build),)).run(timeout=30)
   self.assertFalse(view.exception);self.assertEqual((profile.calls,review.calls,rank.calls,citation.calls,competitor.calls),(0,0,0,0,0));self.assertGreaterEqual(len(view.download_button),11)
