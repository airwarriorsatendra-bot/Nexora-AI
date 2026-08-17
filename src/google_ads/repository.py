"""Additive async SQLite persistence for Google Ads imported snapshots."""
from __future__ import annotations
import json
from collections.abc import Sequence
from pathlib import Path
from src.google_ads.domain import GoogleAdsAudit
from src.research.repositories.sqlite_repository import SQLiteRepository
class GoogleAdsRepository(SQLiteRepository[GoogleAdsAudit]):
 @property
 def schema_statements(self)->Sequence[str]:return("CREATE TABLE IF NOT EXISTS google_ads_audits(audit_id TEXT PRIMARY KEY,customer_id TEXT NOT NULL,date_from TEXT NOT NULL,date_to TEXT NOT NULL,source TEXT NOT NULL,captured_at TEXT NOT NULL,audit_json TEXT NOT NULL,UNIQUE(customer_id,date_from,date_to,source))","CREATE INDEX IF NOT EXISTS idx_google_ads_audits_customer ON google_ads_audits(customer_id)","CREATE INDEX IF NOT EXISTS idx_google_ads_audits_period ON google_ads_audits(date_from,date_to)")
 def __init__(self,path:str|Path):super().__init__(path)
 async def save(self,audit:GoogleAdsAudit)->GoogleAdsAudit:
  await self.initialize();await self._execute("INSERT INTO google_ads_audits(audit_id,customer_id,date_from,date_to,source,captured_at,audit_json) VALUES(?,?,?,?,?,?,?) ON CONFLICT(customer_id,date_from,date_to,source) DO UPDATE SET audit_id=excluded.audit_id,captured_at=excluded.captured_at,audit_json=excluded.audit_json",(str(audit.audit_id),audit.account.customer_id,audit.period.date_from.isoformat(),audit.period.date_to.isoformat(),audit.source,audit.captured_at.isoformat(),json.dumps(audit.model_dump(mode='json'),separators=(',',':'))),operation_name="save Google Ads audit");return audit
 async def list_recent(self,limit:int=50)->list[GoogleAdsAudit]:
  await self.initialize();rows=await self._fetchall("SELECT audit_json FROM google_ads_audits ORDER BY captured_at DESC LIMIT ?",(max(1,min(limit,500)),),operation_name="list Google Ads audits");return[GoogleAdsAudit.model_validate_json(r['audit_json']) for r in rows]
