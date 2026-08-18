"""Concurrency-safe additive SQLite persistence for rank tracking."""
from __future__ import annotations
from collections.abc import Sequence
from pathlib import Path
from uuid import UUID
from src.rank_tracking.domain import RankCheck,TrackedKeyword,TrackingContext
from src.research.repositories.sqlite_repository import SQLiteRepository
class RankTrackingRepository(SQLiteRepository[TrackedKeyword]):
 @property
 def schema_statements(self)->Sequence[str]:return (
  "CREATE TABLE IF NOT EXISTS tracked_keywords(keyword_id TEXT PRIMARY KEY,keyword TEXT NOT NULL,target_domain TEXT NOT NULL,active INTEGER NOT NULL,updated_at TEXT NOT NULL,keyword_json TEXT NOT NULL)","CREATE INDEX IF NOT EXISTS idx_tracked_keywords_active ON tracked_keywords(active,keyword)",
  "CREATE TABLE IF NOT EXISTS rank_checks(check_id TEXT PRIMARY KEY,keyword_id TEXT NOT NULL,checked_at TEXT NOT NULL,context_json TEXT NOT NULL,depth INTEGER NOT NULL,target_position INTEGER,provider TEXT NOT NULL,check_json TEXT NOT NULL,FOREIGN KEY(keyword_id) REFERENCES tracked_keywords(keyword_id) ON DELETE CASCADE)","CREATE INDEX IF NOT EXISTS idx_rank_checks_keyword ON rank_checks(keyword_id,checked_at DESC)","CREATE INDEX IF NOT EXISTS idx_rank_checks_position ON rank_checks(target_position,checked_at DESC)",
  "CREATE TABLE IF NOT EXISTS serp_results(check_id TEXT NOT NULL,position INTEGER NOT NULL,domain TEXT NOT NULL,result_json TEXT NOT NULL,PRIMARY KEY(check_id,position),FOREIGN KEY(check_id) REFERENCES rank_checks(check_id) ON DELETE CASCADE)","CREATE INDEX IF NOT EXISTS idx_serp_results_domain ON serp_results(domain,position)")
 async def save_keyword(self,k):
  await self.initialize();await self._execute("INSERT INTO tracked_keywords(keyword_id,keyword,target_domain,active,updated_at,keyword_json) VALUES(?,?,?,?,?,?) ON CONFLICT(keyword_id) DO UPDATE SET keyword=excluded.keyword,target_domain=excluded.target_domain,active=excluded.active,updated_at=excluded.updated_at,keyword_json=excluded.keyword_json",(str(k.keyword_id),k.keyword,k.target_domain,int(k.active),k.updated_at.isoformat(),k.model_dump_json()),operation_name="save tracked keyword");return k
 async def get_keyword(self,kid):
  await self.initialize();r=await self._fetchone("SELECT keyword_json FROM tracked_keywords WHERE keyword_id=?",(str(kid),),operation_name="get tracked keyword");return None if r is None else TrackedKeyword.model_validate_json(r["keyword_json"])
 async def list_keywords(self,active_only=False):
  await self.initialize();w=" WHERE active=1" if active_only else "";rows=await self._fetchall(f"SELECT keyword_json FROM tracked_keywords{w} ORDER BY keyword COLLATE NOCASE",(),operation_name="list tracked keywords");return [TrackedKeyword.model_validate_json(r["keyword_json"]) for r in rows]
 async def delete_keyword(self,kid):await self.initialize();return await self._execute("DELETE FROM tracked_keywords WHERE keyword_id=?",(str(kid),),operation_name="delete tracked keyword")
 async def save_check(self,c):
  await self.initialize();await self._execute("INSERT INTO rank_checks(check_id,keyword_id,checked_at,context_json,depth,target_position,provider,check_json) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(check_id) DO NOTHING",(str(c.check_id),str(c.keyword_id),c.checked_at.isoformat(),c.context.model_dump_json(),c.depth,c.target_position,c.provider,c.model_dump_json()),operation_name="save rank check");await self._executemany("INSERT INTO serp_results(check_id,position,domain,result_json) VALUES(?,?,?,?) ON CONFLICT(check_id,position) DO NOTHING",[(str(c.check_id),r.position,r.domain,r.model_dump_json()) for r in c.results],operation_name="save SERP results");return c
 async def history(self,kid,context=None,limit=500):
  await self.initialize();clauses=["keyword_id=?"];p=[str(kid)];
  if context is not None:clauses.append("context_json=?");p.append(context.model_dump_json())
  p.append(max(1,min(limit,1000)));rows=await self._fetchall(f"SELECT check_json FROM rank_checks WHERE {' AND '.join(clauses)} ORDER BY checked_at ASC,rowid ASC LIMIT ?",p,operation_name="get rank history");return [RankCheck.model_validate_json(r["check_json"]) for r in rows]
 async def latest(self,kid,context):
  h=await self.history(kid,context,1000);return h[-1] if h else None
 async def latest_checks(self):
  await self.initialize();rows=await self._fetchall("SELECT rc.check_json FROM rank_checks rc WHERE rc.rowid=(SELECT r2.rowid FROM rank_checks r2 WHERE r2.keyword_id=rc.keyword_id ORDER BY r2.checked_at DESC,r2.rowid DESC LIMIT 1) ORDER BY rc.checked_at DESC",(),operation_name="get current ranks");return [RankCheck.model_validate_json(r["check_json"]) for r in rows]
