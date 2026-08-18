"""Dashboard adapter for Backlink Intelligence 2.0."""
from __future__ import annotations
from collections.abc import Callable
import pandas as pd
from src.backlinks.composition import BacklinkApplication,BacklinkComposition,BacklinkSettings
from src.backlinks.domain.intelligence import AuthorityScope
from src.backlinks.dto.backlink_discovery import BacklinkDiscoveryRequest
from src.backlinks.dto.backlink_verification import BacklinkVerificationRequest

class BacklinksDashboardWorkflow:
 def __init__(self,application_factory:Callable[[],BacklinkApplication]|None=None):self._application_factory=application_factory or self._build_application
 async def _use(self,operation):
  application=self._application_factory()
  try:return await operation(application)
  finally:await application.aclose()
 async def discover(self,target_url,candidates):return await self._use(lambda app:app.discovery_service.discover(BacklinkDiscoveryRequest(target_url=target_url,candidate_urls=candidates)))
 async def verify(self,source_url,target_url):return await self._use(lambda app:app.verification_service.verify(BacklinkVerificationRequest(source_url=source_url,target_url=target_url)))
 async def list_backlinks(self,target_domain=""):return await self._use(lambda app:app.repository.list_backlinks(target_domain=target_domain or None,limit=500))
 async def preview_authority(self,targets,scope="url",force=False):return await self._use(lambda app:app.intelligence_service.preview_authority(targets,AuthorityScope(scope),force=force))
 async def enrich_authority(self,targets,scope="url",force=False):return await self._use(lambda app:app.intelligence_service.enrich_authority(targets,AuthorityScope(scope),force=force))
 async def snapshot(self,target_domain=""):
  async def load(app):
   links=await app.repository.list_backlinks(target_domain=target_domain or None,limit=500);opportunities=await app.repository.list_opportunities(limit=500);authority=await app.repository.authority_history(limit=500);prospects=await app.repository.list_prospects(limit=500);prospect_history=await app.repository.prospect_history(limit=500);referring=await app.repository.referring_domains(target_domain) if target_domain else [];intersect=app.intelligence_service.link_intersect(links,target_domain,set()) if target_domain else ();anchors=app.intelligence_service.anchor_summary(links);reclamation=app.intelligence_service.reclamation(links,{})
   return {"backlinks":links,"opportunities":opportunities,"authority":authority,"prospects":prospects,"prospect_history":prospect_history,"referring_domains":referring,"intersect":intersect,"competitor_gaps":intersect,"anchors":anchors,"reclamation":reclamation,"moz_configured":app.authority_provider is not None}
  return await self._use(load)
 @staticmethod
 def _build_application():return BacklinkComposition(BacklinkSettings.from_environment()).build()

def _frame(items):return pd.DataFrame([item.model_dump(mode="json") if hasattr(item,"model_dump") else item for item in items])
def backlinks_to_dataframe(backlinks):return _frame(backlinks)
def authority_to_dataframe(items):return _frame(items)
def prospects_to_dataframe(items):return _frame(items)
def referring_domains_to_dataframe(items):return _frame(items)
def intersect_to_dataframe(items):return _frame(items)
def backlink_report(snapshot):
 return "# Nexora Backlink Intelligence Report\n\nProvider-observed and Nexora-observed evidence only.\n\n"+"\n".join((f"- Observed backlinks: {len(snapshot['backlinks'])}",f"- Observed referring domains: {len(snapshot['referring_domains'])}",f"- Authority observations: {len(snapshot['authority'])}",f"- Prospects: {len(snapshot['prospects'])}","- No backlink causality or guaranteed ranking gain is claimed."))
