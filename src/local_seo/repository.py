"""Additive SQLite persistence for Local SEO audits and evidence history."""
from __future__ import annotations
import json
from collections.abc import Sequence
from pathlib import Path
from src.local_seo.domain import BusinessLocation,BusinessProfileAccount,CitationTarget,LocalCitation,LocalCompetitor,LocalHistoryEvent,LocalLandingPage,LocalOpportunity,LocalQueryEvidence,LocalRankObservation,LocalReview,LocalSEOAudit,NAPEvidence
from src.research.repositories.sqlite_repository import SQLiteRepository

class LocalSEORepository(SQLiteRepository[LocalSEOAudit]):
 @property
 def schema_statements(self)->Sequence[str]:return (
  "CREATE TABLE IF NOT EXISTS local_seo_audits(website TEXT PRIMARY KEY,audit_id TEXT NOT NULL,audited_at TEXT NOT NULL,overall_score REAL NOT NULL,audit_json TEXT NOT NULL)",
  "CREATE INDEX IF NOT EXISTS idx_local_seo_audits_time ON local_seo_audits(audited_at DESC)",
  "CREATE INDEX IF NOT EXISTS idx_local_seo_audits_score ON local_seo_audits(overall_score DESC)",
  "CREATE TABLE IF NOT EXISTS local_locations(location_id TEXT PRIMARY KEY,business_id TEXT NOT NULL,observed_at TEXT NOT NULL,location_json TEXT NOT NULL)",
  "CREATE TABLE IF NOT EXISTS local_gbp_accounts(account_id TEXT PRIMARY KEY,observed_at TEXT NOT NULL,account_json TEXT NOT NULL)",
  "CREATE TABLE IF NOT EXISTS local_nap_evidence(evidence_id TEXT PRIMARY KEY,location_id TEXT NOT NULL,observed_at TEXT NOT NULL,evidence_json TEXT NOT NULL,FOREIGN KEY(location_id) REFERENCES local_locations(location_id))",
  "CREATE TABLE IF NOT EXISTS local_reviews(review_id TEXT PRIMARY KEY,location_id TEXT NOT NULL,observed_at TEXT NOT NULL,review_json TEXT NOT NULL,FOREIGN KEY(location_id) REFERENCES local_locations(location_id))",
  "CREATE TABLE IF NOT EXISTS local_rank_observations(observation_id TEXT PRIMARY KEY,identity_key TEXT NOT NULL UNIQUE,location_id TEXT NOT NULL,observed_at TEXT NOT NULL,rank_json TEXT NOT NULL,FOREIGN KEY(location_id) REFERENCES local_locations(location_id))",
  "CREATE TABLE IF NOT EXISTS local_citation_targets(target_id TEXT PRIMARY KEY,identity_key TEXT NOT NULL UNIQUE,location_id TEXT NOT NULL,target_json TEXT NOT NULL,FOREIGN KEY(location_id) REFERENCES local_locations(location_id))",
  "CREATE TABLE IF NOT EXISTS local_citations(citation_id TEXT PRIMARY KEY,identity_key TEXT NOT NULL UNIQUE,location_id TEXT NOT NULL,observed_at TEXT NOT NULL,citation_json TEXT NOT NULL,FOREIGN KEY(location_id) REFERENCES local_locations(location_id))",
  "CREATE TABLE IF NOT EXISTS local_competitors(competitor_id TEXT PRIMARY KEY,identity_key TEXT NOT NULL UNIQUE,location_id TEXT NOT NULL,observed_at TEXT NOT NULL,competitor_json TEXT NOT NULL,FOREIGN KEY(location_id) REFERENCES local_locations(location_id))",
  "CREATE TABLE IF NOT EXISTS local_opportunities(opportunity_id TEXT PRIMARY KEY,identity_key TEXT NOT NULL UNIQUE,location_id TEXT,observed_at TEXT NOT NULL,opportunity_json TEXT NOT NULL)",
  "CREATE TABLE IF NOT EXISTS local_queries(identity_key TEXT PRIMARY KEY,query_json TEXT NOT NULL)",
  "CREATE TABLE IF NOT EXISTS local_landing_pages(url TEXT PRIMARY KEY,page_json TEXT NOT NULL)",
  "CREATE TABLE IF NOT EXISTS local_history(event_id TEXT PRIMARY KEY,location_id TEXT,evidence_type TEXT NOT NULL,provider TEXT NOT NULL,observed_at TEXT NOT NULL,event_json TEXT NOT NULL)",
  "CREATE INDEX IF NOT EXISTS idx_local_reviews_location_time ON local_reviews(location_id,observed_at DESC)",
  "CREATE INDEX IF NOT EXISTS idx_local_ranks_location_time ON local_rank_observations(location_id,observed_at DESC)",
  "CREATE INDEX IF NOT EXISTS idx_local_history_location_time ON local_history(location_id,observed_at DESC)")
 def __init__(self,path:str|Path)->None:super().__init__(path)
 async def save(self,audit:LocalSEOAudit)->LocalSEOAudit:
  await self.initialize();await self._execute("INSERT INTO local_seo_audits(website,audit_id,audited_at,overall_score,audit_json) VALUES(?,?,?,?,?) ON CONFLICT(website) DO UPDATE SET audit_id=excluded.audit_id,audited_at=excluded.audited_at,overall_score=excluded.overall_score,audit_json=excluded.audit_json",(str(audit.business.website),str(audit.audit_id),audit.audited_at.isoformat(),audit.overall_score,audit.model_dump_json()),operation_name="save local audit");return audit
 async def find(self,website:str)->LocalSEOAudit|None:
  await self.initialize();row=await self._fetchone("SELECT audit_json FROM local_seo_audits WHERE website=?",(website,),operation_name="find local audit");return None if row is None else LocalSEOAudit.model_validate_json(row["audit_json"])
 async def list_recent(self,limit:int=50)->list[LocalSEOAudit]:return await self._list("local_seo_audits","audit_json",LocalSEOAudit,limit,"audited_at")
 async def _list(self,table,field,model,limit=1000,order="rowid"):
  await self.initialize();rows=await self._fetchall(f"SELECT {field} FROM {table} ORDER BY {order} DESC LIMIT ?",(max(1,min(limit,10000)),),operation_name=f"list {table}");return [model.model_validate_json(x[field]) for x in rows]
 async def save_location(self,x:BusinessLocation):
  await self.initialize();await self._execute("INSERT INTO local_locations(location_id,business_id,observed_at,location_json) VALUES(?,?,?,?) ON CONFLICT(location_id) DO UPDATE SET business_id=excluded.business_id,observed_at=excluded.observed_at,location_json=excluded.location_json",(x.location_id,str(x.business_id),x.observed_at.isoformat(),x.model_dump_json()),operation_name="save local location");return x
 async def save_gbp_account(self,x:BusinessProfileAccount):
  await self.initialize();await self._execute("INSERT INTO local_gbp_accounts(account_id,observed_at,account_json) VALUES(?,?,?) ON CONFLICT(account_id) DO UPDATE SET observed_at=excluded.observed_at,account_json=excluded.account_json",(x.account_id,x.observed_at.isoformat(),x.model_dump_json()),operation_name="save GBP account");return x
 async def save_review(self,x:LocalReview):
  await self.initialize();await self._execute("INSERT INTO local_reviews(review_id,location_id,observed_at,review_json) VALUES(?,?,?,?) ON CONFLICT(review_id) DO UPDATE SET observed_at=excluded.observed_at,review_json=excluded.review_json",(x.review_id,x.location_id,x.observed_at.isoformat(),x.model_dump_json()),operation_name="save local review");return x
 async def save_nap_evidence(self,x:NAPEvidence):
  await self.initialize();await self._execute("INSERT INTO local_nap_evidence(evidence_id,location_id,observed_at,evidence_json) VALUES(?,?,?,?) ON CONFLICT(evidence_id) DO UPDATE SET observed_at=excluded.observed_at,evidence_json=excluded.evidence_json",(str(x.evidence_id),x.location_id,x.observed_at.isoformat(),x.model_dump_json()),operation_name="save NAP evidence");return x
 async def _save_identity(self,table,id_field,identity,location_id,observed_at,field,x):
  await self.initialize();identifier=str(getattr(x,id_field));await self._execute(f"INSERT INTO {table}({id_field},identity_key,location_id,observed_at,{field}) VALUES(?,?,?,?,?) ON CONFLICT(identity_key) DO UPDATE SET observed_at=excluded.observed_at,{field}=excluded.{field}",(identifier,identity,location_id,observed_at.isoformat(),x.model_dump_json()),operation_name=f"save {table}");return x
 async def save_rank(self,x:LocalRankObservation):return await self._save_identity("local_rank_observations","observation_id","|".join((x.location_id,x.query.casefold(),x.location_descriptor.casefold(),x.device.casefold(),x.engine.casefold(),x.result_type.value,x.observed_at.isoformat())),x.location_id,x.observed_at,"rank_json",x)
 async def save_citation(self,x:LocalCitation):return await self._save_identity("local_citations","citation_id",f"{x.location_id}|{x.directory.casefold()}|{(x.listing_url or '').casefold()}",x.location_id,x.observed_at,"citation_json",x)
 async def save_competitor(self,x:LocalCompetitor):return await self._save_identity("local_competitors","competitor_id",f"{x.location_id}|{x.domain.casefold()}|{(x.observed_query or '').casefold()}",x.location_id,x.observed_at,"competitor_json",x)
 async def save_target(self,x:CitationTarget):
  await self.initialize();await self._execute("INSERT INTO local_citation_targets(target_id,identity_key,location_id,target_json) VALUES(?,?,?,?) ON CONFLICT(identity_key) DO UPDATE SET target_json=excluded.target_json",(str(x.target_id),f"{x.location_id}|{x.directory.casefold()}",x.location_id,x.model_dump_json()),operation_name="save citation target");return x
 async def save_opportunity(self,x:LocalOpportunity):return await self._save_identity("local_opportunities","opportunity_id",f"{x.location_id or ''}|{x.opportunity_type}|{x.title}",x.location_id,x.observed_at,"opportunity_json",x)
 async def save_history(self,x:LocalHistoryEvent):
  await self.initialize();await self._execute("INSERT OR IGNORE INTO local_history(event_id,location_id,evidence_type,provider,observed_at,event_json) VALUES(?,?,?,?,?,?)",(str(x.event_id),x.location_id,x.evidence_type,x.provider,x.observed_at.isoformat(),x.model_dump_json()),operation_name="save local history");return x
 async def save_query(self,x:LocalQueryEvidence):
  await self.initialize();key=f"{x.query.casefold()}|{(x.location_modifier or '').casefold()}";await self._execute("INSERT INTO local_queries(identity_key,query_json) VALUES(?,?) ON CONFLICT(identity_key) DO UPDATE SET query_json=excluded.query_json",(key,x.model_dump_json()),operation_name="save local query");return x
 async def save_landing_page(self,x:LocalLandingPage):
  await self.initialize();await self._execute("INSERT INTO local_landing_pages(url,page_json) VALUES(?,?) ON CONFLICT(url) DO UPDATE SET page_json=excluded.page_json",(x.url,x.model_dump_json()),operation_name="save local landing page");return x
 async def list_locations(self,limit=1000):return await self._list("local_locations","location_json",BusinessLocation,limit,"observed_at")
 async def count_locations(self):return await self._count("local_locations")
 async def list_gbp_accounts(self,limit=100):return await self._list("local_gbp_accounts","account_json",BusinessProfileAccount,limit,"observed_at")
 async def list_reviews(self,limit=10000):return await self._list("local_reviews","review_json",LocalReview,limit,"observed_at")
 async def count_reviews(self):return await self._count("local_reviews")
 async def list_nap_evidence(self,limit=10000):return await self._list("local_nap_evidence","evidence_json",NAPEvidence,limit,"observed_at")
 async def list_ranks(self,limit=10000):return await self._list("local_rank_observations","rank_json",LocalRankObservation,limit,"observed_at")
 async def list_citations(self,limit=10000):return await self._list("local_citations","citation_json",LocalCitation,limit,"observed_at")
 async def list_targets(self,limit=10000):return await self._list("local_citation_targets","target_json",CitationTarget,limit)
 async def list_competitors(self,limit=10000):return await self._list("local_competitors","competitor_json",LocalCompetitor,limit,"observed_at")
 async def list_opportunities(self,limit=10000):return await self._list("local_opportunities","opportunity_json",LocalOpportunity,limit,"observed_at")
 async def count_opportunities(self):return await self._count("local_opportunities")
 async def _count(self,table):
  await self.initialize();row=await self._fetchone(f"SELECT COUNT(*) AS count FROM {table}",operation_name=f"count {table}");return int(row["count"])
 async def list_history(self,limit=10000):return await self._list("local_history","event_json",LocalHistoryEvent,limit,"observed_at")
 async def list_queries(self,limit=10000):return await self._list("local_queries","query_json",LocalQueryEvidence,limit)
 async def list_landing_pages(self,limit=10000):return await self._list("local_landing_pages","page_json",LocalLandingPage,limit)
