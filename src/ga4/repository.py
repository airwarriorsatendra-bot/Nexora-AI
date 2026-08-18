from __future__ import annotations
import hashlib,json
from collections.abc import Sequence
from pathlib import Path
from src.research.repositories.sqlite_repository import SQLiteRepository
from src.ga4.domain import GA4Snapshot,GA4Dimension
class GA4Repository(SQLiteRepository[GA4Snapshot]):
 @property
 def schema_statements(self)->Sequence[str]:
  return ('CREATE TABLE IF NOT EXISTS ga4_properties(property_id TEXT PRIMARY KEY,property_json TEXT NOT NULL)','CREATE TABLE IF NOT EXISTS ga4_snapshots(snapshot_id TEXT PRIMARY KEY,snapshot_key TEXT UNIQUE NOT NULL,dimensions_json TEXT NOT NULL,captured_at TEXT NOT NULL,snapshot_json TEXT NOT NULL)','CREATE TABLE IF NOT EXISTS ga4_rows(snapshot_key TEXT,row_number INTEGER,row_json TEXT,PRIMARY KEY(snapshot_key,row_number))')
 async def save(self,s:GA4Snapshot)->GA4Snapshot:
  await self.initialize();key=self.key(s)
  await self._execute('INSERT INTO ga4_properties(property_id,property_json) VALUES(?,?) ON CONFLICT(property_id) DO UPDATE SET property_json=excluded.property_json',(s.property.property_id,s.property.model_dump_json()),operation_name='save GA4 property')
  await self._execute('INSERT INTO ga4_snapshots(snapshot_id,snapshot_key,dimensions_json,captured_at,snapshot_json) VALUES(?,?,?,?,?) ON CONFLICT(snapshot_key) DO NOTHING',(str(s.snapshot_id),key,json.dumps([d.value for d in s.dimensions]),s.captured_at.isoformat(),s.model_dump_json()),operation_name='save GA4 snapshot')
  await self._executemany('INSERT INTO ga4_rows(snapshot_key,row_number,row_json) VALUES(?,?,?) ON CONFLICT(snapshot_key,row_number) DO NOTHING',[(key,i,r.model_dump_json()) for i,r in enumerate(s.records)],operation_name='save GA4 rows');return s
 async def latest(self,dimensions:tuple[GA4Dimension,...]=())->GA4Snapshot|None:
  await self.initialize();row=await self._fetchone('SELECT snapshot_json FROM ga4_snapshots WHERE dimensions_json=? ORDER BY captured_at DESC,rowid DESC LIMIT 1',(json.dumps([d.value for d in dimensions]),),operation_name='latest GA4');return None if row is None else GA4Snapshot.model_validate_json(row['snapshot_json'])
 @staticmethod
 def key(s):
  d=s.model_dump(mode='json');d.pop('snapshot_id');d.pop('captured_at');return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest()
