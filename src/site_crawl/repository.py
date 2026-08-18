"""Additive async SQLite persistence for site crawl history."""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from uuid import UUID

from src.research.repositories.sqlite_repository import SQLiteRepository
from src.site_crawl.domain import SiteCrawl


class SiteCrawlRepository(SQLiteRepository[SiteCrawl]):
    @property
    def schema_statements(self) -> Sequence[str]:
        return (
            "CREATE TABLE IF NOT EXISTS site_crawls(crawl_id TEXT PRIMARY KEY,request_fingerprint TEXT NOT NULL,start_url TEXT NOT NULL,started_at TEXT NOT NULL,completed_at TEXT NOT NULL,crawl_json TEXT NOT NULL)",
            "CREATE INDEX IF NOT EXISTS idx_site_crawls_history ON site_crawls(start_url,completed_at DESC)",
            "CREATE TABLE IF NOT EXISTS site_crawl_pages(crawl_id TEXT NOT NULL,normalized_url TEXT NOT NULL,status_code INTEGER,depth INTEGER NOT NULL,page_json TEXT NOT NULL,PRIMARY KEY(crawl_id,normalized_url),FOREIGN KEY(crawl_id) REFERENCES site_crawls(crawl_id) ON DELETE CASCADE)",
            "CREATE TABLE IF NOT EXISTS site_crawl_links(crawl_id TEXT NOT NULL,link_number INTEGER NOT NULL,source_url TEXT NOT NULL,target_url TEXT NOT NULL,link_json TEXT NOT NULL,PRIMARY KEY(crawl_id,link_number),FOREIGN KEY(crawl_id) REFERENCES site_crawls(crawl_id) ON DELETE CASCADE)",
            "CREATE TABLE IF NOT EXISTS site_crawl_issues(crawl_id TEXT NOT NULL,issue_number INTEGER NOT NULL,code TEXT NOT NULL,affected_url TEXT NOT NULL,issue_json TEXT NOT NULL,PRIMARY KEY(crawl_id,issue_number),FOREIGN KEY(crawl_id) REFERENCES site_crawls(crawl_id) ON DELETE CASCADE)",
        )

    async def save(self, crawl: SiteCrawl) -> SiteCrawl:
        await self.initialize()
        await self._execute("INSERT INTO site_crawls(crawl_id,request_fingerprint,start_url,started_at,completed_at,crawl_json) VALUES(?,?,?,?,?,?) ON CONFLICT(crawl_id) DO NOTHING", (str(crawl.crawl_id), crawl.request.fingerprint, str(crawl.request.start_url), crawl.started_at.isoformat(), crawl.completed_at.isoformat(), crawl.model_dump_json()), operation_name="save site crawl")
        await self._executemany("INSERT INTO site_crawl_pages(crawl_id,normalized_url,status_code,depth,page_json) VALUES(?,?,?,?,?) ON CONFLICT(crawl_id,normalized_url) DO NOTHING", [(str(crawl.crawl_id), p.normalized_url, p.status_code, p.depth, p.model_dump_json()) for p in crawl.pages], operation_name="save crawl pages")
        await self._executemany("INSERT INTO site_crawl_links(crawl_id,link_number,source_url,target_url,link_json) VALUES(?,?,?,?,?) ON CONFLICT(crawl_id,link_number) DO NOTHING", [(str(crawl.crawl_id), i, link.source_url, link.target_url, link.model_dump_json()) for i, link in enumerate(crawl.links)], operation_name="save crawl links")
        await self._executemany("INSERT INTO site_crawl_issues(crawl_id,issue_number,code,affected_url,issue_json) VALUES(?,?,?,?,?) ON CONFLICT(crawl_id,issue_number) DO NOTHING", [(str(crawl.crawl_id), i, issue.code, issue.affected_url, issue.model_dump_json()) for i, issue in enumerate(crawl.issues)], operation_name="save crawl issues")
        return crawl

    async def get(self, crawl_id: UUID) -> SiteCrawl | None:
        await self.initialize(); row = await self._fetchone("SELECT crawl_json FROM site_crawls WHERE crawl_id=?", (str(crawl_id),), operation_name="get site crawl")
        return None if row is None else SiteCrawl.model_validate_json(row["crawl_json"])

    async def history(self, start_url: str | None = None, limit: int = 50) -> list[SiteCrawl]:
        await self.initialize(); where = " WHERE start_url=?" if start_url else ""; params = (start_url, max(1, min(limit, 200))) if start_url else (max(1, min(limit, 200)),)
        rows = await self._fetchall(f"SELECT crawl_json FROM site_crawls{where} ORDER BY completed_at ASC,rowid ASC LIMIT ?", params, operation_name="site crawl history")
        return [SiteCrawl.model_validate_json(row["crawl_json"]) for row in rows]

    async def latest(self, start_url: str | None = None) -> SiteCrawl | None:
        rows = await self.history(start_url, 200)
        return rows[-1] if rows else None

