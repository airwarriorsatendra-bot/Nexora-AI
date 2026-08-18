from __future__ import annotations
import asyncio
from decimal import Decimal
import httpx
from src.core.constants import DEFAULT_RETRY_COUNT,GSC_TOKEN_URL,GA4_DATA_API_BASE_URL,GA4_ADMIN_API_BASE_URL
from src.core.exceptions import AuthenticationError,AuthorizationError,ExternalAPIError
from src.ga4.domain import GA4Property,GA4Record
class RealGA4Provider:
 def __init__(self,client_id,client_secret,refresh_token,http_client=None):self.c=(client_id,client_secret,refresh_token);self.h=http_client;self.own=http_client is None
 async def aclose(self):
  if self.own and self.h:await self.h.aclose()
 async def _h(self):
  if self.h is None:self.h=httpx.AsyncClient(timeout=30)
  return self.h
 async def _token(self):
  if not all(self.c):raise AuthenticationError('Google OAuth configuration is incomplete.')
  r=await (await self._h()).post(GSC_TOKEN_URL,data={'client_id':self.c[0],'client_secret':self.c[1],'refresh_token':self.c[2],'grant_type':'refresh_token'})
  if r.status_code in(400,401):raise AuthenticationError('Google OAuth credentials were rejected.')
  if r.status_code>=400:raise ExternalAPIError('Google OAuth token request failed.')
  return r.json().get('access_token')
 async def _request(self,method,url,json=None):
  token=await self._token()
  for i in range(DEFAULT_RETRY_COUNT+1):
   try:r=await (await self._h()).request(method,url,headers={'Authorization':f'Bearer {token}'},json=json)
   except httpx.HTTPError as e:
    if i<DEFAULT_RETRY_COUNT:await asyncio.sleep(.1*2**i);continue
    raise ExternalAPIError('Google Analytics request failed.') from e
   if r.status_code in(429,500,502,503,504) and i<DEFAULT_RETRY_COUNT:await asyncio.sleep(.1*2**i);continue
   if r.status_code==401:raise AuthenticationError('Google Analytics authentication failed.')
   if r.status_code==403:raise AuthorizationError('Google account is not authorized for Analytics.')
   if r.status_code>=400:raise ExternalAPIError(f'Google Analytics request failed with HTTP {r.status_code}.')
   return r.json()
 async def list_properties(self):
  data=await self._request('GET',f'{GA4_ADMIN_API_BASE_URL}/accountSummaries');return tuple(GA4Property(property_id=p['property'].removeprefix('properties/'),display_name=p.get('displayName',''),account_id=a.get('account','').removeprefix('accounts/'),account_name=a.get('displayName','')) for a in data.get('accountSummaries',[]) for p in a.get('propertySummaries',[]))
 async def run_report(self,q):
  data=await self._request('POST',f'{GA4_DATA_API_BASE_URL}/properties/{q.property.property_id}:runReport',{'dateRanges':[{'startDate':q.period.start_date.isoformat(),'endDate':q.period.end_date.isoformat()}],'dimensions':[{'name':d.value} for d in q.dimensions],'metrics':[{'name':m} for m in q.metrics],'limit':str(q.limit)})
  return tuple(GA4Record(dimensions=q.dimensions,keys=tuple(v.get('value','') for v in row.get('dimensionValues',[])),metrics={m:Decimal(v.get('value','0')) for m,v in zip(q.metrics,row.get('metricValues',[]))}) for row in data.get('rows',[]))
class OfflineGA4Provider:
 def __init__(self,properties=(),records=None):self.properties=properties;self.records=records or {};self.closed=False
 async def list_properties(self):return tuple(self.properties)
 async def run_report(self,q):return self.records.get(tuple(d.value for d in q.dimensions),())
 async def aclose(self):self.closed=True
