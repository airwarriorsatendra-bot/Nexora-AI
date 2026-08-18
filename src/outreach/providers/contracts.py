"""Replaceable offline-safe Outreach provider contracts and deterministic fakes."""
from __future__ import annotations
from typing import Any,Protocol,Sequence,runtime_checkable
from src.outreach.domain.crm import OutreachContact,OutreachReply,VerificationState

@runtime_checkable
class ContactDiscoveryProvider(Protocol):
 provider_name:str
 async def discover(self,domain:str)->Sequence[OutreachContact]:...
 async def aclose(self)->None:...

@runtime_checkable
class EmailVerificationProvider(Protocol):
 provider_name:str
 async def verify(self,email:str)->VerificationState:...
 async def aclose(self)->None:...

@runtime_checkable
class ReplyProvider(Protocol):
 provider_name:str
 async def replies(self,tracked_messages:Sequence[Any]=())->Sequence[OutreachReply]:...
 async def aclose(self)->None:...

class FakeContactDiscoveryProvider:
 provider_name="fake_contact"
 def __init__(self,contacts=()):self.contacts=tuple(contacts);self.calls=[]
 async def discover(self,domain):self.calls.append(domain);return tuple(x for x in self.contacts if x.domain==domain)
 async def aclose(self):return None

class FakeEmailVerificationProvider:
 provider_name="fake_verification"
 def __init__(self,state=VerificationState.VERIFIED):self.state=state;self.calls=[]
 async def verify(self,email):self.calls.append(email);return self.state
 async def aclose(self):return None

class FakeReplyProvider:
 provider_name="fake_reply"
 def __init__(self,replies=()):self.items=tuple(replies);self.calls=0
 async def replies(self,tracked_messages=()):self.calls+=1;return self.items
 async def aclose(self):return None
