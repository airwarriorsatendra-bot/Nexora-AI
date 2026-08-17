"""
==========================================================
NEXORA AI
Utility Repository
Part 1 of 2
==========================================================

Shared database utilities used by all repositories.

Responsibilities
----------------
- Generic lookup queries
- Table statistics
- Distinct values
- Aggregations
- Shared reusable SQL helpers

Contains NO business logic.
"""

from __future__ import annotations

from typing import Any
from typing import Sequence

from dashboard.repositories.base_repository import BaseRepository


class UtilityRepository(BaseRepository):
    """
    Shared utility repository.
    """

    # ==================================================
    # Table Statistics
    # ==================================================

    def row_count(
        self,
        table: str,
    ) -> int:
        """
        Return total rows.
        """

        self._validate_table(table)

        return self.count(table)

    # --------------------------------------------------

    def table_empty(
        self,
        table: str,
    ) -> bool:
        """
        True if table contains no rows.
        """

        return self.row_count(table) == 0

    # --------------------------------------------------

    def table_size(
        self,
        table: str,
    ) -> dict[str, int]:
        """
        Basic table statistics.
        """

        self._validate_table(table)

        total = self.count(table)

        return {

            "rows": total,

        }

    # ==================================================
    # Generic Lookup Helpers
    # ==================================================

    def value_exists(
        self,
        table: str,
        column: str,
        value: Any,
    ) -> bool:

        return self.exists(
            table,
            column,
            value,
        )

    # --------------------------------------------------

    def distinct_values(
        self,
        table: str,
        column: str,
    ) -> list[Any]:
        """
        Return distinct values.
        """

        self._validate_table(table)

        self._validate_column(column)

        rows = self.fetch_all(
            f"""
            SELECT DISTINCT {column}
            FROM {table}
            ORDER BY {column}
            """
        )

        return [

            row[column]

            for row in rows

        ]

    # --------------------------------------------------

    def column_values(
        self,
        table: str,
        column: str,
    ) -> list[Any]:
        """
        Return every value from a column.
        """

        self._validate_table(table)

        self._validate_column(column)

        rows = self.fetch_all(
            f"""
            SELECT {column}
            FROM {table}
            """
        )

        return [

            row[column]

            for row in rows

        ]

    # ==================================================
    # Aggregation Helpers
    # ==================================================

    def group_count(
        self,
        table: str,
        column: str,
    ) -> dict[Any, int]:
        """
        GROUP BY count helper.
        """

        self._validate_table(table)

        self._validate_column(column)

        rows = self.fetch_all(
            f"""
            SELECT
                {column},
                COUNT(*) AS total
            FROM {table}
            GROUP BY {column}
            ORDER BY total DESC
            """
        )

        return {

            row[column]: row["total"]

            for row in rows

        }

    # --------------------------------------------------

    def max_value(
        self,
        table: str,
        column: str,
    ) -> Any:
        """
        Maximum value.
        """

        self._validate_table(table)

        self._validate_column(column)

        return self.fetch_value(
            f"""
            SELECT MAX({column})
            FROM {table}
            """
        )

    # --------------------------------------------------

    def min_value(
        self,
        table: str,
        column: str,
    ) -> Any:
        """
        Minimum value.
        """

        self._validate_table(table)

        self._validate_column(column)

        return self.fetch_value(
            f"""
            SELECT MIN({column})
            FROM {table}
            """
        )

    # --------------------------------------------------

    def average(
        self,
        table: str,
        column: str,
    ) -> float:
        """
        Average numeric value.
        """

        self._validate_table(table)

        self._validate_column(column)

        value = self.fetch_value(
            f"""
            SELECT AVG({column})
            FROM {table}
            """
        )

        return float(value or 0)

    # ==================================================
    # Generic Search Helpers
    # ==================================================

    def lookup(
        self,
        table: str,
        keyword: str,
        columns: Sequence[str],
    ) -> list[dict[str, Any]]:
        """
        Generic LIKE search.
        """

        self._validate_table(table)

        if not columns:

            return []

        for column in columns:

            self._validate_column(column)

        conditions = " OR ".join(

            f"{column} LIKE ?"

            for column in columns

        )

        sql = f"""
            SELECT *
            FROM {table}
            WHERE {conditions}
        """

        params = tuple(

            f"%{keyword}%"

            for _ in columns

        )

        return self.fetch_all(
            sql,
            params,
        )
    # ==================================================
    # Generic Value Helpers
    # ==================================================

    def first_value(
        self,
        table: str,
        column: str,
        *,
        where: str = "",
        params: Sequence[Any] = (),
    ) -> Any:
        """
        Return first value from a column.
        """

        self._validate_table(table)
        self._validate_column(column)

        sql = f"""
            SELECT {column}
            FROM {table}
        """

        if where:
            sql += f"\nWHERE {where}"

        sql += "\nLIMIT 1"

        return self.fetch_value(
            sql,
            tuple(params),
        )

    # --------------------------------------------------

    def last_value(
        self,
        table: str,
        column: str,
        *,
        order_by: str = "id",
    ) -> Any:
        """
        Return latest value.
        """

        self._validate_table(table)
        self._validate_column(column)
        self._validate_column(order_by)

        return self.fetch_value(
            f"""
            SELECT {column}
            FROM {table}
            ORDER BY {order_by} DESC
            LIMIT 1
            """
        )

    # --------------------------------------------------

    def values_in(
        self,
        table: str,
        column: str,
        values: Sequence[Any],
    ) -> list[dict[str, Any]]:
        """
        Return rows whose column
        exists in supplied values.
        """

        self._validate_table(table)
        self._validate_column(column)

        if not values:
            return []

        placeholders = ",".join(
            "?"
            for _ in values
        )

        sql = f"""
            SELECT *
            FROM {table}
            WHERE {column}
            IN ({placeholders})
        """

        return self.fetch_all(
            sql,
            tuple(values),
        )

    # ==================================================
    # Metadata Helpers
    # ==================================================

    def table_columns(
        self,
        table: str,
    ) -> list[str]:
        """
        Return column names.
        """

        self._validate_table(table)

        rows = self.fetch_all(
            f"""
            PRAGMA table_info({table})
            """
        )

        return [
            row["name"]
            for row in rows
        ]

    # --------------------------------------------------

    def table_information(
        self,
        table: str,
    ) -> list[dict[str, Any]]:
        """
        Return PRAGMA table_info().
        """

        self._validate_table(table)

        return self.fetch_all(
            f"""
            PRAGMA table_info({table})
            """
        )

    # ==================================================
    # Repository Helpers
    # ==================================================

    def vacuum(self) -> None:
        """
        Execute VACUUM.
        """

        self.db.connection.execute(
            "VACUUM"
        )

    # --------------------------------------------------

    def analyze(self) -> None:
        """
        Execute ANALYZE.
        """

        self.db.connection.execute(
            "ANALYZE"
        )

    # --------------------------------------------------

    def integrity_status(
        self,
    ) -> bool:
        """
        True if integrity check passes.
        """

        return (
            self.integrity_check().lower()
            == "ok"
        )

    # --------------------------------------------------

    def database_statistics(
        self,
    ) -> dict[str, Any]:
        """
        Overall database statistics.
        """

        stats: dict[str, Any] = {}

        for table in sorted(
            self._ALLOWED_TABLES
        ):

            if self.db.table_exists(table):

                stats[table] = self.count(
                    table
                )

        stats["connected"] = (
            self.is_connected
        )

        stats["integrity"] = (
            self.integrity_check()
        )

        return stats

    # ==================================================
    # Convenience Helpers
    # ==================================================

    @staticmethod
    def unique(
        values: Sequence[Any],
    ) -> list[Any]:
        """
        Preserve order while removing duplicates.
        """

        seen = set()

        result = []

        for value in values:

            if value in seen:
                continue

            seen.add(value)

            result.append(value)

        return result

    # --------------------------------------------------

    @staticmethod
    def compact(
        values: Sequence[Any],
    ) -> list[Any]:
        """
        Remove None and empty strings.
        """

        return [
            value
            for value in values
            if value not in (
                None,
                "",
            )
        ]

    # --------------------------------------------------

    @staticmethod
    def as_dict(
        rows: Sequence[dict[str, Any]],
        key: str,
    ) -> dict[Any, dict[str, Any]]:
        """
        Index rows by key.
        """

        return {
            row[key]: row
            for row in rows
            if key in row
        }

    # ==================================================
    # Repository Information
    # ==================================================

    @property
    def repository_name(
        self,
    ) -> str:
        return "UtilityRepository"

    # --------------------------------------------------

    def __repr__(
        self,
    ) -> str:

        return (
            f"{self.repository_name}()"
        )