"""Async SQLite persistence for deterministic SEO audits."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from src.core.exceptions import RepositoryError
from src.research.repositories.sqlite_repository import SQLiteRepository
from src.seo.domain.seo_audit import SEOAudit


class SEOAuditRepository(SQLiteRepository[SEOAudit]):
    """Store one current audit per URL through idempotent URL upserts."""

    TABLE_NAME = "seo_audits"

    @property
    def schema_statements(self) -> Sequence[str]:
        return (
            """
            CREATE TABLE IF NOT EXISTS seo_audits (
                url TEXT PRIMARY KEY,
                audit_id TEXT NOT NULL,
                audited_at TEXT NOT NULL,
                overall_score REAL NOT NULL,
                audit_json TEXT NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_seo_audits_audited_at ON seo_audits(audited_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_seo_audits_score ON seo_audits(overall_score DESC)",
        )

    def __init__(self, database_path: str | Path) -> None:
        super().__init__(database_path)

    async def save(self, audit: SEOAudit) -> SEOAudit:
        await self.initialize()
        data = audit.model_dump(mode="json")
        try:
            await self._execute(
                """
                INSERT INTO seo_audits(url, audit_id, audited_at, overall_score, audit_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    audit_id=excluded.audit_id,
                    audited_at=excluded.audited_at,
                    overall_score=excluded.overall_score,
                    audit_json=excluded.audit_json
                """,
                (
                    str(audit.url),
                    str(audit.audit_id),
                    audit.audited_at.isoformat(),
                    audit.overall_score,
                    json.dumps(data, ensure_ascii=False, separators=(",", ":")),
                ),
                operation_name="save SEO audit",
            )
        except RepositoryError:
            raise
        return audit

    async def find_by_url(self, url: str) -> SEOAudit | None:
        await self.initialize()
        row = await self._fetchone(
            "SELECT audit_json FROM seo_audits WHERE url = ?",
            (url,),
            operation_name="find SEO audit",
        )
        if row is None:
            return None
        try:
            return SEOAudit.model_validate_json(row["audit_json"])
        except (TypeError, ValueError) as exc:
            raise RepositoryError("Stored SEO audit could not be decoded.") from exc

    async def list_recent(self, limit: int = 50) -> list[SEOAudit]:
        await self.initialize()
        rows = await self._fetchall(
            "SELECT audit_json FROM seo_audits ORDER BY audited_at DESC LIMIT ?",
            (max(1, min(limit, 500)),),
            operation_name="list SEO audits",
        )
        try:
            return [SEOAudit.model_validate_json(row["audit_json"]) for row in rows]
        except (TypeError, ValueError) as exc:
            raise RepositoryError("Stored SEO audits could not be decoded.") from exc
