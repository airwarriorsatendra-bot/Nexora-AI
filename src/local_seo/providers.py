"""Replaceable, read-only Local SEO provider boundaries and offline fakes."""
from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable
from uuid import NAMESPACE_URL, uuid5

import httpx

from src.core.constants import DEFAULT_RETRY_COUNT, SEARCH_TIMEOUT_SECONDS
from src.core.exceptions import AuthenticationError, AuthorizationError, ConfigurationError, ExternalAPIError
from src.local_seo.domain import BusinessLocation, BusinessProfileAccount, BusinessProfileRefresh, FreshnessState, LocalCitation, LocalCompetitor, LocalRankObservation, LocalReview, ProviderCapability

class GBPSelectionRequired(ConfigurationError):
    """Raised when an account or location must be selected explicitly."""

@runtime_checkable
class BusinessProfileProvider(Protocol):
    provider_name: str
    capabilities: frozenset[ProviderCapability]
    async def locations(self) -> Sequence[BusinessLocation]: ...
    async def refresh_selected(self) -> BusinessProfileRefresh: ...
    async def aclose(self) -> None: ...

@runtime_checkable
class ReviewProvider(Protocol):
    provider_name: str
    async def reviews(self, location_id: str) -> Sequence[LocalReview]: ...
    async def aclose(self) -> None: ...

@runtime_checkable
class LocalRankProvider(Protocol):
    provider_name: str
    async def ranks(self, location_id: str) -> Sequence[LocalRankObservation]: ...
    async def aclose(self) -> None: ...

@runtime_checkable
class CitationProvider(Protocol):
    provider_name: str
    async def citations(self, location_id: str) -> Sequence[LocalCitation]: ...
    async def aclose(self) -> None: ...

@runtime_checkable
class LocalCompetitorProvider(Protocol):
    provider_name: str
    async def competitors(self, location_id: str) -> Sequence[LocalCompetitor]: ...
    async def aclose(self) -> None: ...

class OfflineBusinessProfileProvider:
    provider_name="OFFLINE";capabilities=frozenset()
    def __init__(self,values=()):self.values=tuple(values);self.calls=0
    async def locations(self):self.calls+=1;return self.values
    async def refresh_selected(self):raise ConfigurationError("GBP_CLIENT_ID, GBP_CLIENT_SECRET, and GBP_REFRESH_TOKEN are required.")
    async def aclose(self):return None
class OfflineReviewProvider:
    provider_name="OFFLINE"
    def __init__(self,values=()):self.values=tuple(values);self.calls=0
    async def reviews(self,location_id):self.calls+=1;return tuple(x for x in self.values if x.location_id==location_id)
    async def aclose(self):return None
class OfflineLocalRankProvider:
    provider_name="OFFLINE"
    def __init__(self,values=()):self.values=tuple(values);self.calls=0
    async def ranks(self,location_id):self.calls+=1;return tuple(x for x in self.values if x.location_id==location_id)
    async def aclose(self):return None
class OfflineCitationProvider:
    provider_name="OFFLINE"
    def __init__(self,values=()):self.values=tuple(values);self.calls=0
    async def citations(self,location_id):self.calls+=1;return tuple(x for x in self.values if x.location_id==location_id)
    async def aclose(self):return None
class OfflineLocalCompetitorProvider:
    provider_name="OFFLINE"
    def __init__(self,values=()):self.values=tuple(values);self.calls=0
    async def competitors(self,location_id):self.calls+=1;return tuple(x for x in self.values if x.location_id==location_id)
    async def aclose(self):return None

class GoogleBusinessProfileProvider:
    """Explicit profile-read adapter. Construction and dashboard renders never call Google."""
    provider_name="GOOGLE_BUSINESS_PROFILE"
    capabilities=frozenset({ProviderCapability.PROFILE_READ})
    token_url="https://oauth2.googleapis.com/token"
    accounts_url="https://mybusinessaccountmanagement.googleapis.com/v1/accounts"
    information_url="https://mybusinessbusinessinformation.googleapis.com/v1"
    read_mask="name,title,storeCode,phoneNumbers,categories,storefrontAddress,websiteUri,regularHours,specialHours,serviceArea,latlng,openInfo,metadata,profile"

    def __init__(self,client_id:str,client_secret:str,refresh_token:str,account_id:str="",location_id:str="",*,client:httpx.AsyncClient|None=None,max_attempts:int=DEFAULT_RETRY_COUNT)->None:
        if not all((client_id.strip(),client_secret.strip(),refresh_token.strip())):raise ConfigurationError("GBP_CLIENT_ID, GBP_CLIENT_SECRET, and GBP_REFRESH_TOKEN are required.")
        self._client_id=client_id.strip();self._client_secret=client_secret.strip();self._refresh_token=refresh_token.strip()
        self.account_id=self._normalize_id(account_id,"accounts");self.location_id=self._normalize_id(location_id,"locations")
        self._client=client or httpx.AsyncClient(timeout=SEARCH_TIMEOUT_SECONDS);self._owns_client=client is None;self._max_attempts=max(1,max_attempts)

    @staticmethod
    def _normalize_id(value:str,kind:str)->str:
        value=value.strip().strip("/");return value if not value or value.startswith(kind+"/") else f"{kind}/{value}"

    async def _request(self,method:str,url:str,**kwargs:Any)->dict[str,Any]:
        for attempt in range(self._max_attempts):
            try:response=await self._client.request(method,url,**kwargs)
            except (httpx.TimeoutException,httpx.TransportError) as exc:
                if attempt+1>=self._max_attempts:raise ExternalAPIError("Google Business Profile request failed due to a transient transport error.") from exc
                await asyncio.sleep(0);continue
            if response.status_code in {429,500,502,503,504} and attempt+1<self._max_attempts:await asyncio.sleep(0);continue
            if response.status_code==401:raise AuthenticationError("Google Business Profile authentication failed.")
            if response.status_code==403:raise AuthorizationError("Google Business Profile access was denied; verify API access, account permissions, and business.manage scope.")
            if response.status_code>=400:raise ExternalAPIError(f"Google Business Profile request failed with HTTP {response.status_code}.")
            try:return response.json()
            except ValueError as exc:raise ExternalAPIError("Google Business Profile returned malformed JSON.") from exc
        raise ExternalAPIError("Google Business Profile request failed.")

    async def _token(self)->str:
        payload=await self._request("POST",self.token_url,data={"client_id":self._client_id,"client_secret":self._client_secret,"refresh_token":self._refresh_token,"grant_type":"refresh_token"})
        token=payload.get("access_token")
        if not isinstance(token,str) or not token:raise AuthenticationError("Google Business Profile token exchange returned no access token.")
        return token

    @staticmethod
    def _select(values:Sequence[dict[str,Any]],configured:str,field:str,label:str)->dict[str,Any]:
        if configured:
            match=next((x for x in values if x.get(field)==configured),None)
            if match is None:raise GBPSelectionRequired(f"Configured GBP_{label.upper()}_ID is not accessible.")
            return match
        if len(values)!=1:raise GBPSelectionRequired(f"Set GBP_{label.upper()}_ID because {len(values)} accessible {label}s were returned.")
        return values[0]

    async def refresh_selected(self)->BusinessProfileRefresh:
        token=await self._token();headers={"Authorization":f"Bearer {token}"}
        payload=await self._request("GET",self.accounts_url,headers=headers,params={"pageSize":10});accounts=payload.get("accounts",[])
        if not isinstance(accounts,list) or not accounts:raise GBPSelectionRequired("No accessible Google Business Profile accounts were returned.")
        account=self._select(accounts,self.account_id,"name","account");account_id=str(account.get("name",""))
        payload=await self._request("GET",f"{self.information_url}/{account_id}/locations",headers=headers,params={"readMask":"name,title,storeCode","pageSize":10});locations=payload.get("locations",[])
        if not isinstance(locations,list) or not locations:raise GBPSelectionRequired("No accessible Google Business Profile locations were returned.")
        selected=self._select(locations,self.location_id,"name","location");location_id=str(selected.get("name",""))
        raw=await self._request("GET",f"{self.information_url}/{location_id}",headers=headers,params={"readMask":self.read_mask});observed=datetime.now(UTC)
        normalized_account=BusinessProfileAccount(account_id=account_id,account_name=str(account.get("accountName",account_id)),account_type=str(account.get("type","")),role=str(account.get("role","")),observed_at=observed)
        return BusinessProfileRefresh(account=normalized_account,location=self._normalize_location(raw,account_id,observed))

    async def locations(self):return ((await self.refresh_selected()).location,)

    @staticmethod
    def _normalize_location(raw:dict[str,Any],account_id:str,observed:datetime)->BusinessLocation:
        address=raw.get("storefrontAddress") or {};phones=raw.get("phoneNumbers") or {};categories=raw.get("categories") or {};latlng=raw.get("latlng") or {};open_info=raw.get("openInfo") or {}
        periods=lambda value:{str(i):str(x) for i,x in enumerate((value or {}).get("periods") or [])};services=(raw.get("serviceArea") or {}).get("places",{}).get("placeInfos",[])
        return BusinessLocation(location_id=str(raw.get("name","")),business_id=uuid5(NAMESPACE_URL,f"gbp:{raw.get('name','')}"),account_id=account_id,business_name=str(raw.get("title","")),primary_category=str((categories.get("primaryCategory") or {}).get("displayName","")),additional_categories=tuple(str(x.get("displayName","")) for x in categories.get("additionalCategories",[]) if x.get("displayName")),address=", ".join(map(str,address.get("addressLines") or [])),locality=str(address.get("locality","")),administrative_area=str(address.get("administrativeArea","")),postal_code=str(address.get("postalCode","")),country=str(address.get("regionCode","")),phone=str(phones.get("primaryPhone","")),website=raw.get("websiteUri"),service_area=tuple(str(x.get("placeName","")) for x in services if x.get("placeName")),latitude=latlng.get("latitude"),longitude=latlng.get("longitude"),regular_hours=periods(raw.get("regularHours")),special_hours=periods(raw.get("specialHours")),profile_status=str(open_info.get("status") or "") or None,source="GOOGLE_BUSINESS_PROFILE_API",provider="GOOGLE_BUSINESS_PROFILE",observed_at=observed,freshness=FreshnessState.FRESH)

    async def aclose(self)->None:
        if self._owns_client:await self._client.aclose()
