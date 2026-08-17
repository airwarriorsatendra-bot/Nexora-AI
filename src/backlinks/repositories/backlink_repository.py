"""Async SQLite persistence for backlink evidence and opportunities."""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from pathlib import Path

from src.backlinks.domain.backlink import Backlink
from src.backlinks.domain.normalization import canonical_url, normalized_domain
from src.backlinks.domain.opportunity import BacklinkOpportunity
from src.core.enums import BacklinkVerificationStatus
from src.core.exceptions import RepositoryError
from src.research.repositories.sqlite_repository import SQLiteRepository


class BacklinkRepository(SQLiteRepository[Backlink]):
    """Persist explicit link identities and separate opportunity records."""

    @property
    def schema_statements(self) -> Sequence[str]:
        return (
            """
            CREATE TABLE IF NOT EXISTS backlinks (
                source_url TEXT NOT NULL,
                target_url TEXT NOT NULL,
                source_domain TEXT NOT NULL,
                target_domain TEXT NOT NULL,
                verification_status TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                backlink_json TEXT NOT NULL,
                PRIMARY KEY(source_url, target_url)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_backlinks_target_domain ON backlinks(target_domain)",
            "CREATE INDEX IF NOT EXISTS idx_backlinks_source_domain ON backlinks(source_domain)",
            "CREATE INDEX IF NOT EXISTS idx_backlinks_status ON backlinks(verification_status)",
            """
            CREATE TABLE IF NOT EXISTS backlink_opportunities (
                url TEXT PRIMARY KEY,
                domain TEXT NOT NULL,
                opportunity_type TEXT NOT NULL,
                status TEXT NOT NULL,
                discovered_at TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                opportunity_json TEXT NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_backlink_opportunities_domain ON backlink_opportunities(domain)",
            "CREATE INDEX IF NOT EXISTS idx_backlink_opportunities_status ON backlink_opportunities(status)",
        )

    def __init__(self, database_path: str | Path) -> None:
        super().__init__(database_path)

    async def save(self, backlink: Backlink) -> Backlink:
        """Idempotently upsert a link by its source/target identity."""
        await self.initialize()
        payload = json.dumps(backlink.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"))
        await self._execute(
            """
            INSERT INTO backlinks(source_url, target_url, source_domain, target_domain, verification_status, first_seen, last_seen, backlink_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_url, target_url) DO UPDATE SET
                source_domain=excluded.source_domain,
                target_domain=excluded.target_domain,
                verification_status=excluded.verification_status,
                first_seen=excluded.first_seen,
                last_seen=excluded.last_seen,
                backlink_json=excluded.backlink_json
            """,
            (
                str(backlink.source_url), str(backlink.target_url), backlink.source_domain,
                backlink.target_domain, backlink.status.value, backlink.first_seen.isoformat(),
                backlink.last_seen.isoformat(), payload,
            ),
            operation_name="save backlink",
        )
        return backlink

    async def save_many(self, backlinks: Iterable[Backlink]) -> int:
        """Save a bounded caller-provided batch without duplicate rows."""
        records = list(backlinks)
        for backlink in records:
            await self.save(backlink)
        return len(records)

    async def find_by_identity(self, source_url: str, target_url: str) -> Backlink | None:
        await self.initialize()
        row = await self._fetchone(
            "SELECT backlink_json FROM backlinks WHERE source_url = ? AND target_url = ?",
            (canonical_url(source_url), canonical_url(target_url)),
            operation_name="find backlink identity",
        )
        return None if row is None else self._decode_backlink(row["backlink_json"])

    async def list_backlinks(
        self, *, target_domain: str | None = None, source_domain: str | None = None,
        status: BacklinkVerificationStatus | None = None, limit: int = 25, offset: int = 0,
    ) -> list[Backlink]:
        await self.initialize()
        clauses: list[str] = []
        parameters: list[object] = []
        if target_domain:
            clauses.append("target_domain = ?")
            parameters.append(normalized_domain(target_domain))
        if source_domain:
            clauses.append("source_domain = ?")
            parameters.append(normalized_domain(source_domain))
        if status:
            clauses.append("verification_status = ?")
            parameters.append(status.value)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        parameters.extend((max(1, min(limit, 500)), max(0, offset)))
        rows = await self._fetchall(
            f"SELECT backlink_json FROM backlinks{where} ORDER BY last_seen DESC LIMIT ? OFFSET ?",
            parameters,
            operation_name="list backlinks",
        )
        return [self._decode_backlink(row["backlink_json"]) for row in rows]

    async def save_opportunity(self, opportunity: BacklinkOpportunity) -> BacklinkOpportunity:
        await self.initialize()
        payload = json.dumps(opportunity.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"))
        await self._execute(
            """
            INSERT INTO backlink_opportunities(url, domain, opportunity_type, status, discovered_at, last_seen, opportunity_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                domain=excluded.domain, opportunity_type=excluded.opportunity_type,
                status=excluded.status, last_seen=excluded.last_seen, opportunity_json=excluded.opportunity_json
            """,
            (str(opportunity.url), opportunity.domain, opportunity.opportunity_type.value,
             opportunity.status.value, opportunity.discovered_at.isoformat(), opportunity.last_seen.isoformat(), payload),
            operation_name="save backlink opportunity",
        )
        return opportunity

    async def list_opportunities(self, *, domain: str | None = None, limit: int = 25, offset: int = 0) -> list[BacklinkOpportunity]:
        await self.initialize()
        where, parameters = "", []
        if domain:
            where, parameters = " WHERE domain = ?", [normalized_domain(domain)]
        parameters.extend((max(1, min(limit, 500)), max(0, offset)))
        rows = await self._fetchall(
            f"SELECT opportunity_json FROM backlink_opportunities{where} ORDER BY last_seen DESC LIMIT ? OFFSET ?",
            parameters, operation_name="list backlink opportunities",
        )
        try:
            return [BacklinkOpportunity.model_validate_json(row["opportunity_json"]) for row in rows]
        except (TypeError, ValueError) as exc:
            raise RepositoryError("Stored backlink opportunity could not be decoded.") from exc

    async def referring_domains(self, target_domain: str) -> list[dict[str, int | str]]:
        """Return only observable domain-level aggregations for a target."""
        await self.initialize()
        rows = await self._fetchall(
            """SELECT source_domain, COUNT(*) AS backlink_count,
                SUM(CASE WHEN verification_status = 'verified' THEN 1 ELSE 0 END) AS verified_count,
                SUM(CASE WHEN verification_status = 'lost' THEN 1 ELSE 0 END) AS lost_count
               FROM backlinks WHERE target_domain = ? GROUP BY source_domain ORDER BY backlink_count DESC""",
            (normalized_domain(target_domain),), operation_name="aggregate referring domains",
        )
        return [dict(row) for row in rows]

    async def delete(self, source_url: str, target_url: str) -> bool:
        await self.initialize()
        return (await self._execute("DELETE FROM backlinks WHERE source_url = ? AND target_url = ?", (canonical_url(source_url), canonical_url(target_url)), operation_name="delete backlink")) > 0

    @staticmethod
    def _decode_backlink(payload: str) -> Backlink:
        try:
            return Backlink.model_validate_json(payload)
        except (TypeError, ValueError) as exc:
            raise RepositoryError("Stored backlink could not be decoded.") from exc
