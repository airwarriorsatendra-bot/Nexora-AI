"""Offline GA4 contracts: reports, persistence, composition, and honest GSC comparison."""
from __future__ import annotations
import asyncio,tempfile,unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
import httpx
from streamlit.testing.v1 import AppTest
from dashboard.ga4_workflow import GA4DashboardWorkflow
from dashboard.ga4 import render_ga4
from src.analytics.gsc_ga4_intelligence import insights
from src.ga4.composition import GA4Composition,GA4Settings
from src.ga4.domain import GA4Property,GA4Record,GA4Snapshot,GA4Dimension,ReportingPeriod
from src.ga4.dto import GA4ReportRequest
from src.ga4.providers import OfflineGA4Provider,RealGA4Provider
from src.core.constants import DEFAULT_RETRY_COUNT
from src.core.exceptions import AuthenticationError,AuthorizationError,ExternalAPIError
from unittest.mock import AsyncMock,patch
from src.ga4.repository import GA4Repository
from src.ga4.service import GA4Service
from src.search_console.domain import SearchConsoleProperty,SearchPerformanceRecord,SearchPerformanceSnapshot,SearchDimension,ReportingPeriod as GSCPeriod
P=GA4Property(property_id='1',display_name='Nexora Demo GA4');PERIOD=ReportingPeriod(start_date=date(2026,8,1),end_date=date(2026,8,15));METRICS=('activeUsers','sessions','engagedSessions','engagementRate','eventCount')
def aggregate():return GA4Record(metrics={'activeUsers':Decimal('1000'),'sessions':Decimal('1400'),'engagedSessions':Decimal('900'),'engagementRate':Decimal('0.642857'),'eventCount':Decimal('7000')})
def ga4_page(workflow):
 from dashboard.ga4 import render_ga4
 render_ga4(workflow)
class GA4Tests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):self.tmp=tempfile.TemporaryDirectory();self.repo=GA4Repository(Path(self.tmp.name)/'ga4.db')
 async def asyncTearDown(self):self.tmp.cleanup()
 async def test_domain_provider_reports_and_empty(self):
  provider=OfflineGA4Provider((P,),{(): (aggregate(),),(GA4Dimension.CHANNEL.value,):(GA4Record(dimensions=(GA4Dimension.CHANNEL,),keys=('Organic Search',),metrics=aggregate().metrics),)})
  service=GA4Service(provider,self.repo);self.assertEqual(await service.list_properties(),(P,));snapshot=await service.refresh(GA4ReportRequest(property=P,period=PERIOD,metrics=METRICS));self.assertEqual(snapshot.totals['sessions'],Decimal('1400'));self.assertEqual(await provider.run_report(GA4ReportRequest(property=P,period=PERIOD,dimensions=(GA4Dimension.EVENT,))),())
 async def test_invalid_period_persistence_idempotency_concurrency_and_close(self):
  with self.assertRaises(ValueError):ReportingPeriod(start_date=PERIOD.end_date,end_date=PERIOD.start_date)
  s=GA4Snapshot(property=P,period=PERIOD,metrics=METRICS,records=(aggregate(),));await asyncio.gather(*(self.repo.save(s) for _ in range(5)));self.assertEqual((await self.repo.latest()).totals['activeUsers'],Decimal('1000'));app=GA4Composition(GA4Settings(Path(self.tmp.name)/'c.db'),provider_factory=lambda _:OfflineGA4Provider()).build();await app.aclose();await app.aclose();self.assertTrue(app.closed)
 async def test_conservative_gsc_bridge_rejects_incompatible_and_never_attributes(self):
  g=SearchPerformanceSnapshot(property=SearchConsoleProperty(site_url='https://example.com',permission_level='owner'),period=GSCPeriod(start_date=PERIOD.start_date,end_date=PERIOD.end_date),dimensions=(SearchDimension.PAGE,),records=(SearchPerformanceRecord(dimensions=(SearchDimension.PAGE,),keys=('https://example.com/service',),clicks=500,impressions=10000,ctr=Decimal('.05'),average_position=Decimal('8.5')),))
  a=GA4Snapshot(property=P,period=PERIOD,dimensions=(GA4Dimension.LANDING_PAGE,),metrics=METRICS,records=(GA4Record(dimensions=(GA4Dimension.LANDING_PAGE,),keys=('/service',),metrics={'engagementRate':Decimal('.7'),'sessions':Decimal('450')}),));found=insights(g,a);self.assertEqual(found[0]['title'],'CTR optimization opportunity');self.assertNotIn('produced',found[0]['evidence']);self.assertEqual(insights(g,a.model_copy(update={'period':ReportingPeriod(start_date=date(2026,7,1),end_date=date(2026,7,15))})),[])
 def test_fake_dashboard_refresh_and_exports(self):
  records={(): (aggregate(),)}
  for dimension,key in ((GA4Dimension.CHANNEL,'Organic Search'),(GA4Dimension.LANDING_PAGE,'/service'),(GA4Dimension.EVENT,'page_view'),(GA4Dimension.DEVICE,'desktop'),(GA4Dimension.COUNTRY,'India'),(GA4Dimension.DATE,'20260801')):records[(dimension.value,)]=(GA4Record(dimensions=(dimension,),keys=(key,),metrics=aggregate().metrics),)
  with tempfile.TemporaryDirectory() as d:
   provider=OfflineGA4Provider((P,),records);app=GA4Composition(GA4Settings(Path(d)/'db'),provider_factory=lambda _:provider).build();view=AppTest.from_function(ga4_page,args=(GA4DashboardWorkflow(factory=lambda:app),));view.run();self.assertFalse(view.exception);next(x for x in view.button if x.key=='ga4-discover').click();view.run();next(x for x in view.button if x.label=='Refresh GA4 data').click();view.run();self.assertFalse(view.exception);self.assertEqual(len(view.metric),4);self.assertTrue(view.download_button)
 async def test_real_provider_oauth_and_retry_statuses_are_bounded_and_safe(self):
  calls={'api':0,'token':0}
  def handler(request):
   if request.url.path=='/token':calls['token']+=1;return httpx.Response(200,json={'access_token':'TEST_ACCESS_TOKEN_DO_NOT_EXPOSE'})
   calls['api']+=1
   return httpx.Response(429 if calls['api']<=DEFAULT_RETRY_COUNT else 200,json={'accountSummaries':[]})
  client=httpx.AsyncClient(transport=httpx.MockTransport(handler));provider=RealGA4Provider('id','TEST_CLIENT_SECRET_DO_NOT_EXPOSE','TEST_REFRESH_TOKEN_DO_NOT_EXPOSE',client)
  with patch('src.ga4.providers.asyncio.sleep',new=AsyncMock()) as sleep:
   self.assertEqual(await provider.list_properties(),());self.assertEqual(calls['api'],DEFAULT_RETRY_COUNT+1);self.assertEqual(sleep.await_count,DEFAULT_RETRY_COUNT)
  await client.aclose()
 async def test_real_provider_deterministic_and_transport_failures_are_safe(self):
  def auth_handler(request):return httpx.Response(400,json={'error':'invalid_grant'})
  client=httpx.AsyncClient(transport=httpx.MockTransport(auth_handler));p=RealGA4Provider('id','TEST_CLIENT_SECRET_DO_NOT_EXPOSE','TEST_REFRESH_TOKEN_DO_NOT_EXPOSE',client)
  with self.assertRaises(AuthenticationError) as e:await p.list_properties()
  self.assertNotIn('TEST_',str(e.exception));await client.aclose();self.assertTrue(client.is_closed)
  attempts={'n':0}
  def denied(request):
   if request.url.path=='/token':return httpx.Response(200,json={'access_token':'TEST_ACCESS_TOKEN_DO_NOT_EXPOSE'})
   attempts['n']+=1;return httpx.Response(403,json={})
  client=httpx.AsyncClient(transport=httpx.MockTransport(denied));p=RealGA4Provider('id','secret','refresh',client)
  with self.assertRaises(AuthorizationError):await p.list_properties()
  self.assertEqual(attempts['n'],1);await client.aclose();self.assertTrue(client.is_closed)
  def timeout(request):
   if request.url.path=='/token':return httpx.Response(200,json={'access_token':'TEST_ACCESS_TOKEN_DO_NOT_EXPOSE'})
   raise httpx.TimeoutException('network down')
  client=httpx.AsyncClient(transport=httpx.MockTransport(timeout));p=RealGA4Provider('id','secret','refresh',client)
  with patch('src.ga4.providers.asyncio.sleep',new=AsyncMock()) as sleep:
   with self.assertRaises(ExternalAPIError) as e:await p.list_properties()
   self.assertIsNotNone(e.exception.__cause__);self.assertEqual(sleep.await_count,DEFAULT_RETRY_COUNT)
  await client.aclose();self.assertTrue(client.is_closed)
 async def test_real_provider_oauth_success_and_owned_client_cleanup(self):
  calls={'token':0,'api':0}
  def handler(request):
   if request.url.path=='/token':
    calls['token']+=1;return httpx.Response(200,json={'access_token':'TEST_ACCESS_TOKEN_DO_NOT_EXPOSE'})
   calls['api']+=1;return httpx.Response(200,json={'accountSummaries':[]})
  client=httpx.AsyncClient(transport=httpx.MockTransport(handler));p=RealGA4Provider('id','TEST_CLIENT_SECRET_DO_NOT_EXPOSE','TEST_REFRESH_TOKEN_DO_NOT_EXPOSE',client)
  self.assertEqual(await p.list_properties(),());self.assertEqual(calls,{'token':1,'api':1});await client.aclose();self.assertTrue(client.is_closed)
  owned=RealGA4Provider('id','secret','refresh');owned_client=await owned._h();await owned.aclose();self.assertTrue(owned_client.is_closed)
 async def test_real_provider_retries_all_configured_transient_statuses(self):
  for status in (500,502,503):
   calls={'api':0}
   def handler(request,status=status):
    if request.url.path=='/token':return httpx.Response(200,json={'access_token':'TEST_ACCESS_TOKEN_DO_NOT_EXPOSE'})
    calls['api']+=1;return httpx.Response(status if calls['api']==1 else 200,json={'accountSummaries':[]})
   client=httpx.AsyncClient(transport=httpx.MockTransport(handler));p=RealGA4Provider('id','secret','refresh',client)
   with patch('src.ga4.providers.asyncio.sleep',new=AsyncMock()) as sleep:
    self.assertEqual(await p.list_properties(),());self.assertEqual(calls['api'],2);self.assertEqual(sleep.await_count,1)
   await client.aclose();self.assertTrue(client.is_closed)
  for status in (429,500):
   calls={'api':0}
   def exhausted(request,status=status):
    if request.url.path=='/token':return httpx.Response(200,json={'access_token':'TEST_ACCESS_TOKEN_DO_NOT_EXPOSE'})
    calls['api']+=1;return httpx.Response(status,json={})
   client=httpx.AsyncClient(transport=httpx.MockTransport(exhausted));p=RealGA4Provider('id','secret','refresh',client)
   with patch('src.ga4.providers.asyncio.sleep',new=AsyncMock()) as sleep:
    with self.assertRaises(ExternalAPIError) as error:await p.list_properties()
    self.assertNotIn('TEST_',str(error.exception));self.assertEqual(calls['api'],DEFAULT_RETRY_COUNT+1);self.assertEqual(sleep.await_count,DEFAULT_RETRY_COUNT)
   await client.aclose();self.assertTrue(client.is_closed)
 async def test_real_provider_non_retryable_invalid_property_is_safe(self):
  calls={'api':0}
  def handler(request):
   if request.url.path=='/token':return httpx.Response(200,json={'access_token':'TEST_ACCESS_TOKEN_DO_NOT_EXPOSE'})
   calls['api']+=1;return httpx.Response(404,json={'error':{'message':'property not found'}})
  client=httpx.AsyncClient(transport=httpx.MockTransport(handler));p=RealGA4Provider('id','TEST_CLIENT_SECRET_DO_NOT_EXPOSE','TEST_REFRESH_TOKEN_DO_NOT_EXPOSE',client)
  with patch('src.ga4.providers.asyncio.sleep',new=AsyncMock()) as sleep:
   with self.assertRaises(ExternalAPIError) as error:await p.run_report(GA4ReportRequest(property=P,period=PERIOD,metrics=METRICS))
   self.assertNotIn('TEST_',str(error.exception));self.assertEqual(calls['api'],1);self.assertEqual(sleep.await_count,0)
  await client.aclose();self.assertTrue(client.is_closed)
