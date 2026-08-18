"""Replaceable, read-only Local SEO provider boundaries and offline fakes."""
from __future__ import annotations
from collections.abc import Sequence
from typing import Protocol,runtime_checkable
from src.local_seo.domain import BusinessLocation,LocalCitation,LocalCompetitor,LocalRankObservation,LocalReview,ProviderCapability

@runtime_checkable
class BusinessProfileProvider(Protocol):
 provider_name:str;capabilities:frozenset[ProviderCapability]
 async def locations(self)->Sequence[BusinessLocation]:...
 async def aclose(self)->None:...
@runtime_checkable
class ReviewProvider(Protocol):
 provider_name:str
 async def reviews(self,location_id:str)->Sequence[LocalReview]:...
 async def aclose(self)->None:...
@runtime_checkable
class LocalRankProvider(Protocol):
 provider_name:str
 async def ranks(self,location_id:str)->Sequence[LocalRankObservation]:...
 async def aclose(self)->None:...
@runtime_checkable
class CitationProvider(Protocol):
 provider_name:str
 async def citations(self,location_id:str)->Sequence[LocalCitation]:...
 async def aclose(self)->None:...
@runtime_checkable
class LocalCompetitorProvider(Protocol):
 provider_name:str
 async def competitors(self,location_id:str)->Sequence[LocalCompetitor]:...
 async def aclose(self)->None:...

class OfflineBusinessProfileProvider:
 provider_name="OFFLINE";capabilities=frozenset()
 def __init__(self,values=()):self.values=tuple(values);self.calls=0
 async def locations(self):self.calls+=1;return self.values
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
 """Configuration boundary for future explicit GBP reads; no calls occur implicitly."""
 provider_name="GOOGLE_BUSINESS_PROFILE"
 capabilities=frozenset({ProviderCapability.PROFILE_READ,ProviderCapability.REVIEWS_READ})
 def __init__(self,client_id:str,client_secret:str,refresh_token:str,account_id:str="",location_id:str=""):
  if not all((client_id.strip(),client_secret.strip(),refresh_token.strip())):raise ValueError("GBP_CLIENT_ID, GBP_CLIENT_SECRET, and GBP_REFRESH_TOKEN are required.")
  self._credentials=(client_id.strip(),client_secret.strip(),refresh_token.strip());self.account_id=account_id.strip();self.location_id=location_id.strip()
 async def locations(self):raise RuntimeError("Live GBP reads require a separate explicit verification workflow.")
 async def aclose(self):return None
