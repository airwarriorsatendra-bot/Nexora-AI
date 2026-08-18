"""Offline-first dashboard adapter for Local SEO intelligence."""
from __future__ import annotations
from collections.abc import Callable
import pandas as pd
from src.local_seo.composition import LocalSEOApplication,LocalSEOComposition,LocalSEOSettings
from src.local_seo.dto import LocalSEOAuditRequest

class LocalSEODashboardWorkflow:
 def __init__(self,factory:Callable[[],object]|None=None):self._factory=factory or (lambda:LocalSEOComposition(LocalSEOSettings.from_environment()).build())
 async def execute(self,business,citations=[]):
  app=self._factory()
  try:return await app.audit(LocalSEOAuditRequest(business=business,citations=citations))
  finally:
   close=getattr(app,"aclose",None)
   if close:await close()
 async def snapshot(self):
  app=self._factory()
  try:return await app.snapshot() if isinstance(app,LocalSEOApplication) else None
  finally:
   close=getattr(app,"aclose",None)
   if close:await close()
def frame(values,exclude=()):
 rows=[]
 for value in values:
  row=value.model_dump(mode="json") if hasattr(value,"model_dump") else dict(value)
  for key in exclude:row.pop(key,None)
  rows.append(row)
 return pd.DataFrame(rows)
def issues_to_dataframe(audit):return pd.DataFrame([x.model_dump(mode="json") for x in audit.issues],columns=["code","category","severity","title","description","evidence","recommendation","source"])
def local_report(snapshot):
 summaries=snapshot.review_summaries;coverage=(sum(x.state.value.startswith("PRESENT") for x in snapshot.citations),len(snapshot.citations))
 return "# Nexora Local SEO Intelligence Report\n\n## Executive Summary\nEvidence-backed local intelligence only.\n\n## Business Profile\n"+("Persisted location evidence is available.\n" if snapshot.locations else "Not available.\n")+"\n## NAP Consistency\nEvidence comparison only.\n\n## Review Intelligence\n"+(f"Observed reviews: {sum(x.review_count for x in summaries)}\n" if summaries else "Not available.\n")+f"\n## Citation Intelligence\nConfigured target coverage: {coverage[0]}/{coverage[1] if coverage[1] else 0}.\n\n## Priority Opportunities\n"+"\n".join(f"- {x.title}: {x.evidence}" for x in snapshot.opportunities)+"\n\n## Evidence Limitations\nNo Google Maps rank, Local Pack rank, ranking causality, or guaranteed improvement is claimed.\n"
