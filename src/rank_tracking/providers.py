"""Replaceable SERP provider contract and deterministic offline implementation."""
from __future__ import annotations
from typing import Protocol
from src.rank_tracking.domain import SERPResult, TrackingContext
class SERPProvider(Protocol):
 provider_name:str
 async def search(self,keyword:str,context:TrackingContext,depth:int)->tuple[SERPResult,...]: ...
 async def aclose(self)->None: ...
class OfflineSERPProvider:
 provider_name='offline_serp'
 def __init__(self,responses:dict[str,tuple[SERPResult,...]]|None=None):self.responses=responses or {};self.closed=False
 async def search(self,keyword,context,depth):
  del context
  return tuple(item for item in self.responses.get(keyword,()) if item.position<=depth)
 async def aclose(self):self.closed=True
