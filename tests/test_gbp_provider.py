"""Fully offline Google Business Profile provider and composition tests."""
from __future__ import annotations
import tempfile,unittest
from pathlib import Path
import httpx
from src.core.exceptions import AuthenticationError,AuthorizationError,ConfigurationError,ExternalAPIError
from src.local_seo.composition import LocalSEOComposition,LocalSEOSettings
from src.local_seo.providers import GBPSelectionRequired,GoogleBusinessProfileProvider,OfflineBusinessProfileProvider
from src.local_seo.repository import LocalSEORepository
from src.local_seo.service import LocalSEOAuditService

def response(request:httpx.Request,status:int=200,payload=None):return httpx.Response(status,json=payload or {},request=request)

class GBPProviderTests(unittest.IsolatedAsyncioTestCase):
 async def test_success_normalizes_current_v1_response_and_preserves_provenance(self):
  calls=[]
  def transport(request):
   calls.append(request)
   if "oauth2" in str(request.url):return response(request,payload={"access_token":"access"})
   if "accountmanagement" in str(request.url):return response(request,payload={"accounts":[{"name":"accounts/1","accountName":"Acme","type":"PERSONAL","role":"OWNER"}]})
   if str(request.url).endswith("/accounts/1/locations?readMask=name%2Ctitle%2CstoreCode&pageSize=10"):return response(request,payload={"locations":[{"name":"locations/2","title":"Acme"}]})
   return response(request,payload={"name":"locations/2","title":"Acme","websiteUri":"https://acme.example","phoneNumbers":{"primaryPhone":"123"},"categories":{"primaryCategory":{"displayName":"Dentist"}},"storefrontAddress":{"addressLines":["Main St"],"locality":"Bhopal","regionCode":"IN"},"openInfo":{"status":"OPEN"}})
  client=httpx.AsyncClient(transport=httpx.MockTransport(transport));provider=GoogleBusinessProfileProvider("client","secret","refresh",client=client)
  result=await provider.refresh_selected();self.assertEqual(result.account.account_id,"accounts/1");self.assertEqual(result.location.location_id,"locations/2");self.assertEqual(result.location.provider,"GOOGLE_BUSINESS_PROFILE");self.assertEqual(len(calls),4);self.assertNotIn("secret",str(calls));await client.aclose()
  with tempfile.TemporaryDirectory() as directory:
   repo=LocalSEORepository(Path(directory)/"gbp.db")
   async def unused(_):return ""
   service=LocalSEOAuditService(unused,repo);await service.persist_business_profile(result);await service.persist_business_profile(result)
   self.assertEqual(len(await repo.list_gbp_accounts()),1);self.assertEqual(len(await repo.list_locations()),1);self.assertEqual(len(await repo.list_history()),1)

 async def test_missing_credentials_and_multiple_selection_fail_safely(self):
  with self.assertRaises(ConfigurationError):GoogleBusinessProfileProvider("","secret","refresh")
  def transport(request):
   if "oauth2" in str(request.url):return response(request,payload={"access_token":"access"})
   return response(request,payload={"accounts":[{"name":"accounts/1"},{"name":"accounts/2"}]})
  client=httpx.AsyncClient(transport=httpx.MockTransport(transport));provider=GoogleBusinessProfileProvider("client","secret","refresh",client=client)
  with self.assertRaisesRegex(GBPSelectionRequired,"GBP_ACCOUNT_ID"):await provider.refresh_selected()
  await client.aclose()

 async def test_deterministic_auth_does_not_retry_and_transient_errors_are_bounded(self):
  for status,expected in ((401,1),(403,1),(404,1),(429,3),(500,3)):
   count=0
   def transport(request):
    nonlocal count;count+=1;return response(request,status,{"error":"redacted"})
   client=httpx.AsyncClient(transport=httpx.MockTransport(transport));provider=GoogleBusinessProfileProvider("client","secret-value","refresh-value",client=client,max_attempts=3)
   with self.assertRaises((AuthenticationError,AuthorizationError,ExternalAPIError)):await provider.refresh_selected()
   self.assertEqual(count,expected);await client.aclose()

 async def test_invalid_grant_timeout_missing_fields_and_secret_safe_failures(self):
  count=0
  def invalid(request):return response(request,400,{"error":"invalid_grant"})
  client=httpx.AsyncClient(transport=httpx.MockTransport(invalid));provider=GoogleBusinessProfileProvider("client","secret-value","refresh-value",client=client)
  with self.assertRaises(ExternalAPIError) as caught:await provider.refresh_selected()
  self.assertNotIn("secret-value",str(caught.exception));self.assertNotIn("refresh-value",str(caught.exception));await client.aclose()
  def timeout(request):
   nonlocal count;count+=1;raise httpx.ReadTimeout("timed out",request=request)
  client=httpx.AsyncClient(transport=httpx.MockTransport(timeout));provider=GoogleBusinessProfileProvider("client","secret","refresh",client=client,max_attempts=3)
  with self.assertRaises(ExternalAPIError):await provider.refresh_selected()
  self.assertEqual(count,3);await client.aclose()
  value=GoogleBusinessProfileProvider._normalize_location({"name":"locations/minimal"},"accounts/1",__import__('datetime').datetime.now(__import__('datetime').UTC))
  self.assertEqual(value.business_name,"");self.assertIsNone(value.website);self.assertIsNone(value.profile_status)

 async def test_composition_selects_live_only_when_configured_and_explicit_refresh_persists(self):
  with tempfile.TemporaryDirectory() as directory:
   settings=LocalSEOSettings(Path(directory)/"local.db");app=LocalSEOComposition(settings).build();self.assertIsInstance(app.business_profile,OfflineBusinessProfileProvider);await app.aclose()
   configured=LocalSEOSettings(Path(directory)/"configured.db","client","secret","refresh","1","2");app=LocalSEOComposition(configured).build();self.assertIsInstance(app.business_profile,GoogleBusinessProfileProvider);self.assertEqual(app.business_profile.account_id,"accounts/1");await app.aclose()
