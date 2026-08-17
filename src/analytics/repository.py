"""Async SQLite persistence for immutable Analytics report snapshots."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path

from src.analytics.domain import AnalyticsReport
from src.research.repositories.sqlite_repository import SQLiteRepository


class AnalyticsRepository(SQLiteRepository[AnalyticsReport]):
    """Store snapshots idempotently by deterministic analytical content."""

    def __init__(self, path: str | Path) -> None:
        super().__init__(path)

    @property
    def schema_statements(self) -> Sequence[str]:
        return (
            """
            CREATE TABLE IF NOT EXISTS analytics_snapshots (
                report_id TEXT PRIMARY KEY,
                snapshot_key TEXT UNIQUE,
                date_from TEXT NOT NULL,
                date_to TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                report_json TEXT NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_analytics_snapshots_period ON analytics_snapshots(date_from, date_to)",
            "CREATE INDEX IF NOT EXISTS idx_analytics_snapshots_time ON analytics_snapshots(captured_at DESC)",
        )

    async def initialize(self) -> None:
        await super().initialize()
        columns = await self._fetchall("PRAGMA table_info(analytics_snapshots)", operation_name="inspect analytics schema")
        if "snapshot_key" not in {row["name"] for row in columns}:
            await self._execute("ALTER TABLE analytics_snapshots ADD COLUMN snapshot_key TEXT", operation_name="migrate analytics schema")
        await self._execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_analytics_snapshots_key ON analytics_snapshots(snapshot_key)",
            operation_name="index analytics snapshot identity",
        )

    async def save(self, report: AnalyticsReport) -> AnalyticsReport:
        """Insert once for equivalent evidence, avoiding Streamlit-rerun duplicates."""
        await self.initialize()
        payload = json.dumps(report.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        await self._execute(
            """
            INSERT INTO analytics_snapshots(report_id, snapshot_key, date_from, date_to, captured_at, report_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(snapshot_key) DO NOTHING
            """,
            (
                str(report.report_id),
                self.snapshot_key(report),
                report.period.date_from.isoformat(),
                report.period.date_to.isoformat(),
                report.captured_at.isoformat(),
                payload,
            ),
            operation_name="save analytics snapshot",
        )
        return report

    async def history(
        self,
        *,
        source_module: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 100,
    ) -> list[AnalyticsReport]:
        """Return chronological snapshots, filtering only by persisted evidence."""
        await self.initialize()
        clauses: list[str] = []
        parameters: list[object] = []
        if date_from is not None:
            clauses.append("date_to >= ?")
            parameters.append(date_from)
        if date_to is not None:
            clauses.append("date_from <= ?")
            parameters.append(date_to)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = await self._fetchall(
            f"SELECT report_json FROM analytics_snapshots{where} ORDER BY captured_at ASC, rowid ASC LIMIT ?",
            (*parameters, max(1, min(limit, 500))),
            operation_name="analytics history",
        )
        reports = [AnalyticsReport.model_validate_json(row["report_json"]) for row in rows]
        return reports if source_module is None else [
            report for report in reports if any(kpi.source_module == source_module for kpi in report.kpis)
        ]

    async def latest(self, *, source_module: str | None = None) -> AnalyticsReport | None:
        await self.initialize()
        if source_module is None:
            row = await self._fetchone(
                "SELECT report_json FROM analytics_snapshots ORDER BY captured_at DESC, rowid DESC LIMIT 1",
                operation_name="latest analytics snapshot",
            )
            return None if row is None else AnalyticsReport.model_validate_json(row["report_json"])
        reports = await self.history(source_module=source_module, limit=500)
        return reports[-1] if reports else None

    @staticmethod
    def snapshot_key(report: AnalyticsReport) -> str:
        """Identity excludes generated report/insight IDs and capture timestamps."""
        data = report.model_dump(mode="json")
        data.pop("report_id", None)
        data.pop("captured_at", None)
        for insight in data["insights"]:
            insight.pop("insight_id", None)
            insight.pop("created_at", None)
        encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
