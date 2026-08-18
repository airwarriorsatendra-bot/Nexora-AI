from __future__ import annotations
from typing import Protocol
from src.ai_visibility.domain import Citation,MonitoredPrompt,ProviderCapability,ProviderClassification,ProviderResponse
class AIVisibilityProvider(Protocol):
 @property
 def capability(self)->ProviderCapability:...
 async def run_visibility_prompt(self,prompt:MonitoredPrompt)->ProviderResponse:...
 async def aclose(self)->None:...
class OfflineVisibilityProvider:
 def __init__(self,responses=None,provider="OFFLINE_FIXTURE",model="deterministic-v1",citations_supported=True):self.responses=responses or {};self.calls=0;self._cap=ProviderCapability(provider=provider,model=model,classification=ProviderClassification.GROUNDED_WITH_CITATIONS if citations_supported else ProviderClassification.UNGROUNDED_MODEL_RESPONSE,web_grounding_supported=citations_supported,citations_supported=citations_supported,source_urls_supported=citations_supported,temperature_control_supported=True,seed_supported=True)
 @property
 def capability(self):return self._cap
 async def run_visibility_prompt(self,prompt):
  self.calls+=1;item=self.responses.get(prompt.text);text=item[0] if item else "No configured fixture response.";urls=item[1] if item and len(item)>1 else ();citations=tuple(Citation(url=url,index=i+1) for i,url in enumerate(urls)) if self._cap.citations_supported else ();return ProviderResponse(provider=self._cap.provider,model=self._cap.model,prompt=prompt.text,response_text=text,citations=citations,classification=self._cap.classification)
 async def aclose(self):return None
class TextGenerationVisibilityAdapter:
 def __init__(self,provider,provider_name,model):self.provider=provider;self._cap=ProviderCapability(provider=provider_name.upper()+"_API",model=model,classification=ProviderClassification.UNGROUNDED_MODEL_RESPONSE,temperature_control_supported=True)
 @property
 def capability(self):return self._cap
 async def run_visibility_prompt(self,prompt):
  text=await self.provider.generate(prompt.text);return ProviderResponse(provider=self._cap.provider,model=self._cap.model,prompt=prompt.text,response_text=text,classification=self._cap.classification)
 async def aclose(self):
  close=getattr(self.provider,"aclose",None)
  if close:await close()
