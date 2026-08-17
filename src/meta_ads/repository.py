import json
from collections.abc import Sequence
from pathlib import Path
from src.meta_ads.domain import MetaAudit
from src.research.repositories.sqlite_repository import SQLiteRepository
class MetaAdsRepository(SQLiteRepository[MetaAudit]):
 @property
 def schema_statements(self)->Sequence[str]:return("CREATE TABLE IF NOT EXISTS meta_ads_audits(audit_id TEXT PRIMARY KEY,account_id TEXT NOT NULL,date_from TEXT NOT NULL,date_to TEXT NOT NULL,source TEXT NOT NULL,captured_at TEXT NOT NULL,audit_json TEXT NOT NULL,UNIQUE(account_id,date_from,date_to,source))","CREATE INDEX IF NOT EXISTS idx_meta_ads_account ON meta_ads_audits(account_id)")
 def __init__(self,p:str|Path):super().__init__(p)
 async def save(self,a:MetaAudit):
  await self.initialize();await self._execute("INSERT INTO meta_ads_audits VALUES(?,?,?,?,?,?,?) ON CONFLICT(account_id,date_from,date_to,source) DO UPDATE SET audit_id=excluded.audit_id,captured_at=excluded.captured_at,audit_json=excluded.audit_json",(str(a.audit_id),a.account.ad_account_id,a.period.date_from.isoformat(),a.period.date_to.isoformat(),a.source,a.captured_at.isoformat(),json.dumps(a.model_dump(mode='json'),separators=(',',':'))),operation_name='save Meta audit');return a
 async def list_recent(self):
  await self.initialize();rows=await self._fetchall('SELECT audit_json FROM meta_ads_audits ORDER BY captured_at DESC',operation_name='list Meta audits');return[MetaAudit.model_validate_json(r['audit_json']) for r in rows]
