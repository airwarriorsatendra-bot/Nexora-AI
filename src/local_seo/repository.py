"""Additive async SQLite persistence for Local SEO audit snapshots."""
from __future__ import annotations
import json
from collections.abc import Sequence
from pathlib import Path
from src.local_seo.domain import LocalSEOAudit
from src.research.repositories.sqlite_repository import SQLiteRepository
class LocalSEORepository(SQLiteRepository[LocalSEOAudit]):
 @property
 def schema_statements(self)->Sequence[str]: return ("CREATE TABLE IF NOT EXISTS local_seo_audits(website TEXT PRIMARY KEY,audit_id TEXT NOT NULL,audited_at TEXT NOT NULL,overall_score REAL NOT NULL,audit_json TEXT NOT NULL)","CREATE INDEX IF NOT EXISTS idx_local_seo_audits_time ON local_seo_audits(audited_at DESC)","CREATE INDEX IF NOT EXISTS idx_local_seo_audits_score ON local_seo_audits(overall_score DESC)")
 def __init__(self,path:str|Path)->None: super().__init__(path)
 async def save(self,audit:LocalSEOAudit)->LocalSEOAudit:
  await self.initialize(); await self._execute("INSERT INTO local_seo_audits(website,audit_id,audited_at,overall_score,audit_json) VALUES(?,?,?,?,?) ON CONFLICT(website) DO UPDATE SET audit_id=excluded.audit_id,audited_at=excluded.audited_at,overall_score=excluded.overall_score,audit_json=excluded.audit_json",(str(audit.business.website),str(audit.audit_id),audit.audited_at.isoformat(),audit.overall_score,json.dumps(audit.model_dump(mode='json'),separators=(',',':'))),operation_name="save local audit"); return audit
 async def find(self,website:str)->LocalSEOAudit|None:
  await self.initialize(); row=await self._fetchone("SELECT audit_json FROM local_seo_audits WHERE website=?",(website,),operation_name="find local audit"); return None if row is None else LocalSEOAudit.model_validate_json(row["audit_json"])
 async def list_recent(self,limit:int=50)->list[LocalSEOAudit]:
  await self.initialize(); rows=await self._fetchall("SELECT audit_json FROM local_seo_audits ORDER BY audited_at DESC LIMIT ?",(max(1,min(limit,500)),),operation_name="list local audits"); return [LocalSEOAudit.model_validate_json(row["audit_json"]) for row in rows]
