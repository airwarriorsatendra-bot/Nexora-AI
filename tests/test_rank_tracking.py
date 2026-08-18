"""Offline rank-tracking provider, persistence, service, and dashboard contracts."""
from __future__ import annotations
import asyncio,tempfile,unittest
from datetime import UTC,datetime,timedelta
from decimal import Decimal
from pathlib import Path
import httpx
from streamlit.testing.v1 import AppTest
from unittest.mock import AsyncMock,patch
from dashboard.rank_tracking import render_rank_tracking
from dashboard.rank_tracking_workflow import RankTrackingDashboardWorkflow
from src.core.constants import DEFAULT_RETRY_COUNT
from src.core.exceptions import AuthenticationError,AuthorizationError,ExternalAPIError
from src.rank_tracking.composition import RankTrackingComposition,RankTrackingSettings
from src.rank_tracking.domain import Device,RankChangeType,RankCheck,SERPResult,TrackedKeyword,TrackingContext
from src.rank_tracking.providers import OfflineSERPProvider
from src.rank_tracking.repository import RankTrackingRepository
from src.rank_tracking.serper_provider import SerperRankProvider
from src.rank_tracking.service import RankTrackingService

def result(position,domain,path="/"):return SERPResult(position=position,title=domain,url=f"https://{domain}{path}",domain=domain,snippet="observed")
def rank_page(workflow):
 from dashboard.rank_tracking import render_rank_tracking
 render_rank_tracking(workflow)
class RankTrackingTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):self.tmp=tempfile.TemporaryDirectory();self.repo=RankTrackingRepository(Path(self.tmp.name)/"rank.db");self.keyword=TrackedKeyword(keyword="best product",target_domain="example.com")
 async def asyncTearDown(self):self.tmp.cleanup()
 def test_change_and_matching_semantics(self):
  service=RankTrackingService(OfflineSERPProvider(),self.repo)
  self.assertEqual(service.change(None,8,False).change_type,RankChangeType.BASELINE);self.assertEqual(service.change(None,8,True).change_type,RankChangeType.NEWLY_RANKING);self.assertEqual(service.change(9,5).movement,4);self.assertEqual(service.change(3,8).change_type,RankChangeType.DECLINED);self.assertEqual(service.change(5,5).change_type,RankChangeType.STABLE);self.assertEqual(service.change(12,None).change_type,RankChangeType.LOST)
  self.assertTrue(service.matches(self.keyword,result(1,"www.example.com")));self.assertFalse(service.matches(self.keyword,result(1,"notexample.com")))
  url_keyword=self.keyword.model_copy(update={"target_url":"https://example.com/guide?source=x"});self.assertTrue(service.matches(url_keyword,result(1,"example.com","/guide/")))
 async def test_service_found_not_found_depth_and_newly_ranking(self):
  provider=OfflineSERPProvider({"best product":(result(1,"competitor.test"),)});service=RankTrackingService(provider,self.repo);await service.add_keyword(self.keyword)
  first,change=await service.check(self.keyword,10);self.assertIsNone(first.target_position);self.assertEqual(first.position_label,"NOT_FOUND_IN_TOP_10");self.assertEqual(change.change_type,RankChangeType.BASELINE)
  provider.responses["best product"]=(result(3,"example.com"),);second,change=await service.check(self.keyword,10);self.assertEqual(second.target_position,3);self.assertEqual(change.change_type,RankChangeType.NEWLY_RANKING)
 async def test_repository_crud_history_idempotency_and_concurrency(self):
  await asyncio.gather(*(self.repo.save_keyword(self.keyword) for _ in range(4)));self.assertEqual(len(await self.repo.list_keywords()),1)
  now=datetime.now(UTC);checks=[RankCheck(keyword_id=self.keyword.keyword_id,keyword=self.keyword.keyword,context=self.keyword.context,depth=10,provider="offline",results=(result(i+1,"example.com"),),target_position=i+1,checked_at=now+timedelta(seconds=i)) for i in range(3)]
  await asyncio.gather(*(self.repo.save_check(c) for c in checks));await self.repo.save_check(checks[0]);history=await self.repo.history(self.keyword.keyword_id,self.keyword.context);self.assertEqual([c.target_position for c in history],[1,2,3]);self.assertEqual(len(history[-1].results),1)
 async def test_competitor_aggregation(self):
  provider=OfflineSERPProvider({"best product":(result(1,"a.test"),result(2,"a.test","/two"),result(3,"b.test"),result(4,"example.com"))});service=RankTrackingService(provider,self.repo);await service.add_keyword(self.keyword);await service.check(self.keyword,10);competitors=await service.competitors();a=next(x for x in competitors if x.domain=="a.test");self.assertEqual(a.keywords_observed,1);self.assertEqual(a.top_3_appearances,2);self.assertEqual(a.average_observed_position,Decimal("1.5"))
 async def test_gsc_evidence_remains_separate(self):
  item=self.keyword.model_copy(update={"gsc_average_position":Decimal("9.1"),"gsc_clicks":12,"gsc_impressions":900});service=RankTrackingService(OfflineSERPProvider({item.keyword:(result(4,"example.com"),)}),self.repo);await service.add_keyword(item);check,_=await service.check(item,10);stored=await self.repo.get_keyword(item.keyword_id);self.assertEqual(stored.gsc_average_position,Decimal("9.1"));self.assertEqual(check.target_position,4)
 async def test_serper_success_auth_and_transient_failures(self):
  calls={"api":0}
  def success(request):calls["api"]+=1;return httpx.Response(200,json={"organic":[{"position":2,"title":"Target","link":"https://example.com","snippet":"x"}]})
  client=httpx.AsyncClient(transport=httpx.MockTransport(success));provider=SerperRankProvider("TEST_SECRET_DO_NOT_EXPOSE",client);rows=await provider.search("query",TrackingContext(),10);self.assertEqual(rows[0].position,2);self.assertNotIn("TEST_SECRET",repr(rows));await client.aclose()
  owned=SerperRankProvider("secret");owned_client=await owned._client();await owned.aclose();self.assertTrue(owned_client.is_closed)
  for status,error in ((401,AuthenticationError),(403,AuthorizationError),(404,ExternalAPIError)):
   client=httpx.AsyncClient(transport=httpx.MockTransport(lambda request,s=status:httpx.Response(s,json={})));provider=SerperRankProvider("TEST_SECRET_DO_NOT_EXPOSE",client)
   with self.assertRaises(error) as caught:await provider.search("query",TrackingContext(),10)
   self.assertNotIn("TEST_SECRET",str(caught.exception));await client.aclose()
 async def test_serper_retries_429_5xx_timeout_and_malformed(self):
  for status in (429,500,502,503):
   calls={"n":0}
   def handler(request,s=status):calls["n"]+=1;return httpx.Response(s if calls["n"]==1 else 200,json={} if calls["n"]==1 else {"organic":[]})
   client=httpx.AsyncClient(transport=httpx.MockTransport(handler));provider=SerperRankProvider("secret",client)
   with patch("src.rank_tracking.serper_provider.asyncio.sleep",new=AsyncMock()) as sleep:self.assertEqual(await provider.search("q",TrackingContext(),10),());self.assertEqual(calls["n"],2);self.assertEqual(sleep.await_count,1)
   await client.aclose()
  attempts={"n":0}
  def timeout(request):attempts["n"]+=1;raise httpx.TimeoutException("offline timeout")
  client=httpx.AsyncClient(transport=httpx.MockTransport(timeout));provider=SerperRankProvider("secret",client)
  with patch("src.rank_tracking.serper_provider.asyncio.sleep",new=AsyncMock()) as sleep:
   with self.assertRaises(ExternalAPIError) as caught:await provider.search("q",TrackingContext(),10)
   self.assertEqual(attempts["n"],DEFAULT_RETRY_COUNT+1);self.assertEqual(sleep.await_count,DEFAULT_RETRY_COUNT);self.assertIsNotNone(caught.exception.__cause__)
  await client.aclose()
  attempts={"n":0}
  def limited(request):attempts["n"]+=1;return httpx.Response(429,json={})
  client=httpx.AsyncClient(transport=httpx.MockTransport(limited));provider=SerperRankProvider("secret",client)
  with patch("src.rank_tracking.serper_provider.asyncio.sleep",new=AsyncMock()) as sleep:
   with self.assertRaises(ExternalAPIError):await provider.search("q",TrackingContext(),10)
   self.assertEqual(attempts["n"],DEFAULT_RETRY_COUNT+1);self.assertEqual(sleep.await_count,DEFAULT_RETRY_COUNT)
  await client.aclose()
  client=httpx.AsyncClient(transport=httpx.MockTransport(lambda request:httpx.Response(200,json={"organic":"bad"})));provider=SerperRankProvider("secret",client)
  with self.assertRaises(ExternalAPIError):await provider.search("q",TrackingContext(),10)
  await client.aclose()
 def test_dashboard_offline_fake_flow_and_exports(self):
  with tempfile.TemporaryDirectory() as directory:
   provider=OfflineSERPProvider({"best product":(result(3,"example.com"),)});settings=RankTrackingSettings(Path(directory)/"ui.db",offline=True)
   def factory():return RankTrackingComposition(settings,provider_factory=lambda _:provider).build()
   view=AppTest.from_function(rank_page,args=(RankTrackingDashboardWorkflow(factory=factory),));view.run(timeout=20);self.assertFalse(view.exception);self.assertTrue(view.download_button);self.assertTrue(any(b.key=="rank-check" for b in view.button))
