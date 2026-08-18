"""Dedicated Serper adapter retaining ordered organic SERP positions."""
from __future__ import annotations
import asyncio
from urllib.parse import urlsplit
import httpx
from src.core.constants import DEFAULT_RETRY_COUNT,SEARCH_TIMEOUT_SECONDS
from src.core.exceptions import AuthenticationError,AuthorizationError,ExternalAPIError
from src.rank_tracking.domain import SERPResult,TrackingContext
class SerperRankProvider:
 provider_name='serper'
 def __init__(self,api_key,http_client=None):
  if not api_key.strip():raise ExternalAPIError('Serper API key cannot be empty.')
  self._api_key,self.client,self.owned=api_key.strip(),http_client,http_client is None
 async def aclose(self):
  if self.owned and self.client:await self.client.aclose()
 async def _client(self):
  if self.client is None:self.client=httpx.AsyncClient(timeout=SEARCH_TIMEOUT_SECONDS)
  return self.client
 async def search(self,keyword,context:TrackingContext,depth):
  if not keyword.strip() or depth<1 or depth>100:raise ExternalAPIError('Keyword and search depth are invalid.')
  for attempt in range(DEFAULT_RETRY_COUNT+1):
   payload={'q':keyword,'num':min(depth,100),'gl':context.country.lower(),'hl':context.language,'device':context.device.value}
   if context.location:payload['location']=context.location
   try:r=await (await self._client()).post('https://google.serper.dev/search',headers={'X-API-KEY':self._api_key},json=payload)
   except httpx.HTTPError as e:
    if attempt<DEFAULT_RETRY_COUNT:await asyncio.sleep(.1*2**attempt);continue
    raise ExternalAPIError('SERP request failed.') from e
   if r.status_code in (429,500,502,503,504) and attempt<DEFAULT_RETRY_COUNT:await asyncio.sleep(.1*2**attempt);continue
   if r.status_code==401:raise AuthenticationError('SERP authentication failed.')
   if r.status_code==403:raise AuthorizationError('SERP access is not authorized.')
   if r.status_code>=400:raise ExternalAPIError(f'SERP request failed with HTTP {r.status_code}.')
   try:data=r.json();organic=data.get('organic') if isinstance(data,dict) else None
   except (TypeError,ValueError) as e:raise ExternalAPIError('SERP provider returned invalid JSON.') from e
   if not isinstance(organic,list):raise ExternalAPIError('SERP provider returned invalid organic results.')
   out=[]
   for index,item in enumerate(organic,1):
    if not isinstance(item,dict) or not str(item.get('link','')).strip():continue
    try:
     url=str(item['link']).strip();domain=(urlsplit(url).hostname or '').lower().removeprefix('www.');out.append(SERPResult(position=int(item.get('position',index)),title=str(item.get('title','')),url=url,domain=domain,snippet=str(item.get('snippet',''))))
    except (TypeError,ValueError) as e:raise ExternalAPIError('SERP provider returned a malformed organic result.') from e
   return tuple(out[:depth])
  raise ExternalAPIError('SERP request failed.')
