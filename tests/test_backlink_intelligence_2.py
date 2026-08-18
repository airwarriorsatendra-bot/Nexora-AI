"""Offline certification for Moz Authority and Backlink Intelligence 2.0."""
from __future__ import annotations
import tempfile,unittest
from collections import deque
from datetime import UTC,datetime,timedelta
from pathlib import Path
import httpx
from streamlit.testing.v1 import AppTest
from src.backlinks.composition import BacklinkComposition,BacklinkSettings
from src.backlinks.domain.backlink import Backlink
from src.backlinks.domain.intelligence import AuthorityObservation,AuthorityScope,ObservedGapState,ProspectPriority
from src.backlinks.domain.opportunity import BacklinkOpportunity
from src.backlinks.providers import MozAuthorityProvider,OfflineAuthorityProvider
from src.backlinks.repositories.backlink_repository import BacklinkRepository
from src.backlinks.services.intelligence_service import BacklinkIntelligenceService
from src.core.enums import BacklinkOpportunityType,BacklinkVerificationStatus
from src.core.exceptions import AuthorityProviderError,AuthorityValidationError,BacklinkError

class QueueTransport(httpx.AsyncBaseTransport):
 def __init__(self,outcomes):self.outcomes=deque(outcomes);self.requests=[]
 async def handle_async_request(self,request):
  self.requests.append(request);outcome=self.outcomes.popleft()
  if isinstance(outcome,Exception):raise outcome
  return httpx.Response(outcome[0],json=outcome[1],request=request)

def success(da=40,pa=30):return (200,{"jsonrpc":"2.0","id":"safe","result":{"site_query":{"query":"https://example.com/","scope":"url"},"site_metrics":{"domain_authority":da,"page_authority":pa,"spam_score":0,"link_propensity":0.2,"http_code":200,"root_domain":"example.com","subdomain":"example.com","last_crawled":"2026-01-01","pages_to_page":10,"external_pages_to_page":5,"root_domains_to_page":4,"pages_to_root_domain":100,"external_pages_to_root_domain":50,"root_domains_to_root_domain":20}}})

class BacklinkIntelligence2Tests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.temp=tempfile.TemporaryDirectory();self.repo=BacklinkRepository(Path(self.temp.name)/"b.db")
 async def asyncTearDown(self):self.temp.cleanup()
 async def provider(self,outcomes):
  transport=QueueTransport(outcomes);client=httpx.AsyncClient(transport=transport,headers={"x-moz-token":"secret"});provider=MozAuthorityProvider("secret",client=client,sleep=lambda _:self._noop());return provider,transport,client
 async def _noop(self):return None

 async def test_moz_success_exact_scope_optional_zero_and_provenance(self):
  provider,transport,client=await self.provider([success(0,17)]);value=await provider.observe("https://example.com/",AuthorityScope.URL)
  self.assertEqual((value.domain_authority,value.page_authority,value.spam_score),(0,17,0));self.assertEqual(value.provider,"MOZ");body=transport.requests[0].content.decode();self.assertIn('"scope":"url"',body);self.assertNotIn('"scope":"page"',body);self.assertNotIn("secret",body);await provider.aclose();self.assertFalse(client.is_closed);await client.aclose()

 async def test_moz_jsonrpc_validation_and_malformed_result(self):
  provider,_,client=await self.provider([(200,{"jsonrpc":"2.0","error":{"code":-32652,"status":400,"message":"safe"}})])
  with self.assertRaises(AuthorityValidationError) as raised:await provider.observe("https://example.com/",AuthorityScope.URL)
  self.assertNotIn("secret",str(raised.exception));await client.aclose()
  provider,_,client=await self.provider([(200,{"result":{}})])
  with self.assertRaises(AuthorityProviderError):await provider.observe("https://example.com/",AuthorityScope.URL)
  await client.aclose()

 async def test_nonretryable_and_retryable_statuses_and_timeout(self):
  for status in (400,401,403,404):
   provider,transport,client=await self.provider([(status,{"error":"safe"})])
   with self.assertRaises(AuthorityProviderError):await provider.observe("https://example.com/",AuthorityScope.URL)
   self.assertEqual(len(transport.requests),1);await client.aclose()
  for status in (429,500,502,503,504):
   provider,transport,client=await self.provider([(status,{}),(status,{}),(status,{})])
   with self.assertRaises(AuthorityProviderError) as raised:await provider.observe("https://example.com/",AuthorityScope.URL)
   self.assertEqual(len(transport.requests),3);self.assertIsNotNone(raised.exception.__cause__);await client.aclose()
  request=httpx.Request("POST","https://safe.test");timeout=httpx.ReadTimeout("transient",request=request);provider,transport,client=await self.provider([timeout,timeout,timeout])
  with self.assertRaises(AuthorityProviderError) as raised:await provider.observe("https://example.com/",AuthorityScope.URL)
  self.assertEqual(len(transport.requests),3);self.assertIs(raised.exception.__cause__,timeout);await client.aclose()

 async def test_owned_client_cleanup_and_invalid_scope(self):
  transport=QueueTransport([success()]);created=[]
  def factory(**kwargs):client=httpx.AsyncClient(transport=transport,**kwargs);created.append(client);return client
  provider=MozAuthorityProvider("private",client_factory=factory);await provider.observe("https://example.com/",AuthorityScope.URL);await provider.aclose();self.assertTrue(created[0].is_closed)
  with self.assertRaises(AuthorityValidationError):await provider.observe("https://example.com/","page")

 async def test_cache_dedup_force_batch_and_repository_history(self):
  target="https://example.com/";fixture=AuthorityObservation(target=target,scope=AuthorityScope.URL,domain_authority=20,page_authority=10,spam_score=1);fake=OfflineAuthorityProvider({(target,AuthorityScope.URL):fixture});service=BacklinkIntelligenceService(self.repo,fake,freshness_days=30)
  first=await service.enrich_authority([target,target]);self.assertEqual(len(first),1);self.assertEqual(len(fake.calls),1)
  second=await service.enrich_authority([target]);self.assertEqual(second[0].observation_id,fixture.observation_id);self.assertEqual(len(fake.calls),1)
  await service.enrich_authority([target],force=True);self.assertEqual(len(fake.calls),2);self.assertTrue(await self.repo.authority_history())
  with self.assertRaises(BacklinkError):await service.preview_authority([f"https://e{i}.test/" for i in range(26)])

 async def test_gap_intersect_score_prospect_reclamation_and_anchor(self):
  links=[Backlink(source_url="https://source.test/a",target_url="https://competitor.test/x",anchor_text="Competitor",status=BacklinkVerificationStatus.VERIFIED),Backlink(source_url="https://source.test/b",target_url="https://target.test/x",anchor_text="click here",status=BacklinkVerificationStatus.VERIFIED)]
  service=BacklinkIntelligenceService(self.repo);intersect=service.link_intersect(links,"target.test",{"competitor.test"});self.assertEqual(intersect[0].evidence_state,ObservedGapState.SHARED_OBSERVED);self.assertEqual(service.anchor_summary(links,"Competitor")[0]["anchor_type"],"branded")
  opportunity=BacklinkOpportunity(url="https://source.test/resources",opportunity_type=BacklinkOpportunityType.RESOURCE_PAGE,evidence=("Observed resource page.",));authority=AuthorityObservation(target="https://source.test/resources",scope=AuthorityScope.URL,domain_authority=70,page_authority=40,spam_score=5)
  prospects=await service.prospects([opportunity],authority={"source.test":authority},relevance={"source.test":90},contactability={"source.test":80},competitor_domains={"source.test"},target_page="https://target.test/x");self.assertTrue(0<=prospects[0].score<=100);self.assertIn(prospects[0].priority,set(ProspectPriority));self.assertEqual((await self.repo.list_prospects())[0].score,prospects[0].score)
  lost=links[0].model_copy(update={"status":BacklinkVerificationStatus.LOST});self.assertTrue(service.reclamation([lost],{}));self.assertEqual(service.handoff(prospects[0],authority).prospect_id,prospects[0].prospect_id)

 async def test_cross_source_is_host_scoped_and_technical_precondition(self):
  service=BacklinkIntelligenceService(self.repo);score,ready,reasons=service.cross_source_priority("https://target.test/page",gsc={"url":"https://foreign.test/page","impressions":1000},rank={"url":"https://target.test/page","position":8},crawl={"url":"https://target.test/page","status_code":404,"indexable":False})
  self.assertEqual(score,15);self.assertFalse(ready);self.assertFalse(any("GSC" in x for x in reasons))

 async def test_composition_settings_and_dashboard_no_automatic_moz_call(self):
  fake=OfflineAuthorityProvider();settings=BacklinkSettings(Path(self.temp.name)/"app.db","",30)
  class Crawler:
   async def fetch_html(self,url):return "<html/>"
   async def aclose(self):pass
  app=BacklinkComposition(settings,authority_provider=fake,crawler_factory=Crawler).build();self.assertIs(app.authority_provider,fake);await app.aclose()
  def render_test_page():
   from dashboard.backlinks import render_backlinks
   class Workflow:
    async def snapshot(self,target=""):return {"backlinks":[],"opportunities":[],"authority":[],"prospects":[],"prospect_history":[],"referring_domains":[],"intersect":[],"competitor_gaps":[],"anchors":[],"reclamation":[],"moz_configured":True}
    async def preview_authority(self,*args):raise AssertionError("not clicked")
    async def enrich_authority(self,*args):raise AssertionError("not clicked")
   render_backlinks(Workflow())
  view=AppTest.from_function(render_test_page).run(timeout=30);self.assertFalse(view.exception);self.assertFalse(fake.calls);self.assertTrue(any(x.label=="Authority CSV" for x in view.download_button))
