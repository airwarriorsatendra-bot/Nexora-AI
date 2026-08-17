"""Offline deterministic Local SEO coverage."""
from __future__ import annotations
import tempfile,unittest
from pathlib import Path
from dashboard.local_seo_workflow import LocalSEODashboardWorkflow,issues_to_dataframe
from src.local_seo.domain import Citation,LocalBusiness
from src.local_seo.dto import LocalSEOAuditRequest
from src.local_seo.repository import LocalSEORepository
from src.local_seo.service import LocalSEOAuditService
from src.shared.value_objects.location import Location
HTML='''<html><head><title>Acme Dental in Bhopal</title><script type="application/ld+json">{"@type":"LocalBusiness","telephone":"+91 98765 43210"}</script></head><body>Acme Dental 123 Main Street, Bhopal, Madhya Pradesh +91 98765 43210</body></html>'''
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
