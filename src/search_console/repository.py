"""Async SQLite snapshots for provenance-preserving Search Console data."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path

from src.core.exceptions import RepositoryError
from src.research.repositories.sqlite_repository import SQLiteRepository
from src.search_console.domain import SearchDimension, SearchPerformanceSnapshot


class SearchConsoleRepository(SQLiteRepository[SearchPerformanceSnapshot]):
    @property
    def schema_statements(self) -> Sequence[str]:
        return (
            "CREATE TABLE IF NOT EXISTS gsc_properties(site_url TEXT PRIMARY KEY,permission_level TEXT NOT NULL,updated_at TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS gsc_snapshots(snapshot_id TEXT PRIMARY KEY,snapshot_key TEXT NOT NULL UNIQUE,site_url TEXT NOT NULL,start_date TEXT NOT NULL,end_date TEXT NOT NULL,dimensions_json TEXT NOT NULL,source TEXT NOT NULL,provider TEXT NOT NULL,captured_at TEXT NOT NULL,snapshot_json TEXT NOT NULL,FOREIGN KEY(site_url) REFERENCES gsc_properties(site_url))",
            "CREATE TABLE IF NOT EXISTS gsc_performance_rows(snapshot_key TEXT NOT NULL,row_number INTEGER NOT NULL,keys_json TEXT NOT NULL,clicks INTEGER NOT NULL,impressions INTEGER NOT NULL,ctr TEXT NOT NULL,average_position TEXT NOT NULL,PRIMARY KEY(snapshot_key,row_number),FOREIGN KEY(snapshot_key) REFERENCES gsc_snapshots(snapshot_key) ON DELETE CASCADE)",
            "CREATE INDEX IF NOT EXISTS idx_gsc_snapshots_lookup ON gsc_snapshots(site_url,start_date,end_date,captured_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_gsc_rows_snapshot ON gsc_performance_rows(snapshot_key)",
        )

    def __init__(self, path: str | Path) -> None:
        super().__init__(path)

    async def save(self, snapshot: SearchPerformanceSnapshot) -> SearchPerformanceSnapshot:
        await self.initialize()
        key = self.snapshot_key(snapshot)
        payload = json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        dimensions = json.dumps([item.value for item in snapshot.dimensions], separators=(",", ":"))
        await self._execute("INSERT INTO gsc_properties(site_url,permission_level,updated_at) VALUES(?,?,?) ON CONFLICT(site_url) DO UPDATE SET permission_level=excluded.permission_level,updated_at=excluded.updated_at", (snapshot.property.site_url, snapshot.property.permission_level, snapshot.captured_at.isoformat()), operation_name="save GSC property")
        await self._execute("INSERT INTO gsc_snapshots(snapshot_id,snapshot_key,site_url,start_date,end_date,dimensions_json,source,provider,captured_at,snapshot_json) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(snapshot_key) DO NOTHING", (str(snapshot.snapshot_id), key, snapshot.property.site_url, snapshot.period.start_date.isoformat(), snapshot.period.end_date.isoformat(), dimensions, snapshot.source, snapshot.provider, snapshot.captured_at.isoformat(), payload), operation_name="save GSC snapshot")
        rows = [(key, index, json.dumps(record.keys, ensure_ascii=False, separators=(",", ":")), record.clicks, record.impressions, str(record.ctr), str(record.average_position)) for index, record in enumerate(snapshot.records)]
        await self._executemany("INSERT INTO gsc_performance_rows(snapshot_key,row_number,keys_json,clicks,impressions,ctr,average_position) VALUES(?,?,?,?,?,?,?) ON CONFLICT(snapshot_key,row_number) DO NOTHING", rows, operation_name="save GSC performance rows")
        return snapshot

    async def latest(self, *, site_url: str | None = None, dimensions: tuple[SearchDimension, ...] | None = None) -> SearchPerformanceSnapshot | None:
        await self.initialize()
        clauses: list[str] = []
        parameters: list[object] = []
        if site_url is not None:
            clauses.append("site_url = ?")
            parameters.append(site_url)
        if dimensions is not None:
            clauses.append("dimensions_json = ?")
            parameters.append(json.dumps([item.value for item in dimensions], separators=(",", ":")))
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        row = await self._fetchone(f"SELECT snapshot_json FROM gsc_snapshots{where} ORDER BY captured_at DESC, rowid DESC LIMIT 1", parameters, operation_name="get latest GSC snapshot")
        return None if row is None else self._decode(row["snapshot_json"])

    async def history(self, *, site_url: str | None = None, dimensions: tuple[SearchDimension, ...] | None = None, limit: int = 100) -> list[SearchPerformanceSnapshot]:
        await self.initialize()
        clauses: list[str] = []
        parameters: list[object] = []
        if site_url is not None:
            clauses.append("site_url = ?")
            parameters.append(site_url)
        if dimensions is not None:
            clauses.append("dimensions_json = ?")
            parameters.append(json.dumps([item.value for item in dimensions], separators=(",", ":")))
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = await self._fetchall(f"SELECT snapshot_json FROM gsc_snapshots{where} ORDER BY captured_at ASC, rowid ASC LIMIT ?", (*parameters, max(1, min(limit, 500))), operation_name="get GSC snapshot history")
        return [self._decode(row["snapshot_json"]) for row in rows]

    @staticmethod
    def snapshot_key(snapshot: SearchPerformanceSnapshot) -> str:
        data = snapshot.model_dump(mode="json")
        data.pop("snapshot_id", None)
        data.pop("captured_at", None)
        return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

    @staticmethod
    def _decode(payload: str) -> SearchPerformanceSnapshot:
        try:
            return SearchPerformanceSnapshot.model_validate_json(payload)
        except (TypeError, ValueError) as exc:
            raise RepositoryError("Stored Google Search Console snapshot could not be decoded.") from exc
