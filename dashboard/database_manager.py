"""
==========================================================
NEXORA AI
Database Manager
==========================================================

Centralized SQLite database manager used by all repositories.

Responsibilities:
- Connection management
- Transactions
- Query execution
- Bulk operations
- Health checks
- Backups
- DataFrame support
"""

from __future__ import annotations

import shutil
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd


class DatabaseManager:
    """Enterprise SQLite database manager."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)

        self.connection = sqlite3.connect(
            self.database_path,
            check_same_thread=False,
        )

        self.connection.row_factory = sqlite3.Row

        self.connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        self.connection.execute(
            "PRAGMA journal_mode = WAL"
        )

        self.connection.execute(
            "PRAGMA synchronous = NORMAL"
        )

    # -----------------------------------------------------
    # Transaction Management
    # -----------------------------------------------------

    @contextmanager
    def session(self):
        """
        Transaction wrapper.

        Automatically commits on success
        and rolls back on failure.
        """

        cursor = self.connection.cursor()

        try:
            yield cursor
            self.connection.commit()

        except Exception:
            self.connection.rollback()
            raise

        finally:
            cursor.close()

    # -----------------------------------------------------
    # Execute
    # -----------------------------------------------------

    def execute(
        self,
        query: str,
        parameters: Iterable[Any] = (),
    ) -> None:

        with self.session() as cursor:
            cursor.execute(query, tuple(parameters))

    # -----------------------------------------------------

    def executemany(
        self,
        query: str,
        parameters: Iterable[Iterable[Any]],
    ) -> None:

        with self.session() as cursor:
            cursor.executemany(query, parameters)

    # -----------------------------------------------------
    # Fetch
    # -----------------------------------------------------

    def fetch_one(
        self,
        query: str,
        parameters: Iterable[Any] = (),
    ) -> Optional[Dict[str, Any]]:

        cursor = self.connection.execute(
            query,
            tuple(parameters),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return dict(row)

    # -----------------------------------------------------

    def fetch_all(
        self,
        query: str,
        parameters: Iterable[Any] = (),
    ) -> List[Dict[str, Any]]:

        cursor = self.connection.execute(
            query,
            tuple(parameters),
        )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    # -----------------------------------------------------
    # Scalar
    # -----------------------------------------------------

    def scalar(
        self,
        query: str,
        parameters: Iterable[Any] = (),
    ) -> Any:

        cursor = self.connection.execute(
            query,
            tuple(parameters),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return row[0]

    # -----------------------------------------------------
    # DataFrame
    # -----------------------------------------------------

    def dataframe(
        self,
        query: str,
        parameters: Iterable[Any] = (),
    ) -> pd.DataFrame:

        return pd.read_sql_query(
            query,
            self.connection,
            params=tuple(parameters),
        )

    # -----------------------------------------------------
    # Utilities
    # -----------------------------------------------------

    def table_exists(
        self,
        table_name: str,
    ) -> bool:

        result = self.scalar(
            """
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type='table'
            AND name=?
            """,
            (table_name,),
        )

        return bool(result)

    # -----------------------------------------------------

    def integrity_check(self) -> str:

        result = self.fetch_one(
            "PRAGMA integrity_check;"
        )

        if result is None:
            return "Unknown"

        return next(iter(result.values()))

    # -----------------------------------------------------

    def optimize(self) -> None:

        self.connection.execute("VACUUM")

        self.connection.execute("ANALYZE")

    # -----------------------------------------------------

    def backup(
        self,
        destination: str | Path,
    ) -> None:

        self.connection.commit()

        shutil.copy2(
            self.database_path,
            destination,
        )

    # -----------------------------------------------------

    def close(self) -> None:

        self.connection.close()

    # -----------------------------------------------------

    @property
    def is_connected(self) -> bool:
        try:
            self.connection.execute(
                "SELECT 1"
            )
            return True

        except sqlite3.Error:
            return False