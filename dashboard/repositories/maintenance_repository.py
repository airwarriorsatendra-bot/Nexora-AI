"""Database maintenance operations for Nexora AI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dashboard.repositories.base_repository import BaseRepository


class MaintenanceRepository(BaseRepository):
    """Administrative and health-check helpers for the application database."""

    def optimize_database(self) -> None:
        self.db.optimize()

    def backup_database(self, destination: str | Path) -> None:
        self.db.backup(destination)

    def database_summary(self) -> dict[str, Any]:
        return {
            "path": str(self.db.database_path),
            "size_bytes": self.db.database_path.stat().st_size if self.db.database_path.exists() else 0,
        }

    def verify_required_tables(self) -> bool:
        return all(self.db.table_exists(table) for table in ("schema_version", "prospects", "outreach"))

    def verify_connection(self) -> bool:
        return self.db.is_connected

    def health_report(self) -> dict[str, Any]:
        report = {
            "connected": self.verify_connection(),
            "integrity": self.db.integrity_check(),
            "required_tables": self.verify_required_tables(),
            "database": self.database_summary(),
        }
        report["healthy"] = report["connected"] and report["required_tables"] and report["integrity"].lower() == "ok"
        return report

    def recreate_indexes(self) -> None:
        """Indexes are owned by ``DatabaseInitializer`` and already verified."""

    def run_maintenance(self) -> dict[str, Any]:
        self.optimize_database()
        return self.health_report()

    def reset_database(self, *, keep_schema: bool = True) -> None:
        if not keep_schema:
            raise NotImplementedError("Schema recreation is handled by DatabaseInitializer.")
        with self.transaction():
            for table in ("outreach", "prospects"):
                if self.db.table_exists(table):
                    self.execute(f"DELETE FROM {table}")

    def maintenance_log(self, message: str) -> None:
        self.log_info(f"[Maintenance] {message}")

    def maintenance_warning(self, message: str) -> None:
        self.log_warning(f"[Maintenance] {message}")

    def maintenance_error(self, message: str) -> None:
        self.log_error(f"[Maintenance] {message}")

    @property
    def repository_name(self) -> str:
        return "MaintenanceRepository"

    def __repr__(self) -> str:
        return f"{self.repository_name}(connected={self.db.is_connected})"
