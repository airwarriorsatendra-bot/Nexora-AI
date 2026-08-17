"""
==========================================================
NEXORA AI
Bulk Repository
Part 1 of 2
==========================================================

Centralized bulk operations.

Responsibilities
----------------
- High-performance batch inserts
- Batch updates
- Batch deletes
- Bulk existence checks
- Transaction-safe processing

Contains NO business logic.
"""

from __future__ import annotations

from typing import Any
from typing import Iterable
from typing import Mapping
from typing import Sequence

from dashboard.repositories.base_repository import BaseRepository


class BulkRepository(BaseRepository):
    """
    Generic bulk repository.

    Repository-specific classes should use
    these methods instead of writing
    executemany() repeatedly.
    """

    # ==================================================
    # Generic Bulk Insert
    # ==================================================

    def bulk_insert_records(
        self,
        table: str,
        rows: Sequence[Mapping[str, Any]],
    ) -> int:
        """
        Bulk insert dictionaries.

        Returns inserted row count.
        """

        self._validate_table(table)

        if not rows:
            return 0

        prepared = [
            dict(row)
            for row in rows
        ]

        columns = list(prepared[0].keys())

        placeholders = ",".join(
            "?"
            for _ in columns
        )

        sql = f"""
            INSERT INTO {table}
            ({", ".join(columns)})
            VALUES ({placeholders})
        """

        parameters = [

            tuple(
                row[column]
                for column in columns
            )

            for row in prepared

        ]

        self.executemany(
            sql,
            parameters,
        )

        return len(parameters)

    # ==================================================
    # Generic Bulk Update
    # ==================================================

    def bulk_update_records(
        self,
        table: str,
        primary_key: str,
        rows: Sequence[Mapping[str, Any]],
    ) -> int:
        """
        Bulk update dictionaries.

        Every row must contain
        the primary key.
        """

        self._validate_table(table)

        self._validate_column(primary_key)

        if not rows:
            return 0

        updated = 0

        with self.transaction():

            cursor = self.db.connection.cursor()

            try:

                for row in rows:

                    values = dict(row)

                    if primary_key not in values:
                        continue

                    record_id = values.pop(
                        primary_key
                    )

                    if not values:
                        continue

                    assignments = ", ".join(

                        f"{column}=?"

                        for column in values

                    )

                    sql = f"""
                        UPDATE {table}
                        SET {assignments}
                        WHERE {primary_key}=?
                    """

                    parameters = list(
                        values.values()
                    )

                    parameters.append(
                        record_id
                    )

                    cursor.execute(
                        sql,
                        tuple(parameters),
                    )

                    updated += cursor.rowcount

            finally:

                cursor.close()

        return updated

    # ==================================================
    # Generic Bulk Delete
    # ==================================================

    def bulk_delete_ids(
        self,
        table: str,
        ids: Sequence[Any],
        primary_key: str = "id",
    ) -> int:
        """
        Delete multiple records.
        """

        self._validate_table(table)

        self._validate_column(primary_key)

        if not ids:
            return 0

        placeholders = ",".join(
            "?"
            for _ in ids
        )

        sql = f"""
            DELETE FROM {table}
            WHERE {primary_key}
            IN ({placeholders})
        """

        with self.transaction():

            cursor = self.db.connection.cursor()

            try:

                cursor.execute(
                    sql,
                    tuple(ids),
                )

                return cursor.rowcount

            finally:

                cursor.close()

    # ==================================================
    # Bulk Exists
    # ==================================================

    def existing_values(
        self,
        table: str,
        column: str,
        values: Iterable[Any],
    ) -> set[Any]:
        """
        Return values already existing
        in the database.
        """

        self._validate_table(table)

        self._validate_column(column)

        values = list(values)

        if not values:
            return set()

        placeholders = ",".join(
            "?"
            for _ in values
        )

        sql = f"""
            SELECT {column}
            FROM {table}
            WHERE {column}
            IN ({placeholders})
        """

        rows = self.fetch_all(
            sql,
            tuple(values),
        )

        return {
            row[column]
            for row in rows
        }
    # ==================================================
    # Bulk Upsert
    # ==================================================

    def bulk_upsert(
        self,
        table: str,
        primary_key: str,
        rows: Sequence[Mapping[str, Any]],
    ) -> tuple[int, int]:
        """
        Generic bulk upsert.

        Returns:
            (inserted, updated)
        """

        self._validate_table(table)
        self._validate_column(primary_key)

        if not rows:
            return (0, 0)

        inserted = 0
        updated = 0

        with self.transaction():

            cursor = self.db.connection.cursor()

            try:

                for row in rows:

                    values = dict(row)

                    record_id = values.get(primary_key)

                    # --------------------------
                    # INSERT
                    # --------------------------

                    if record_id is None:

                        columns = list(values.keys())

                        placeholders = ",".join(
                            "?"
                            for _ in columns
                        )

                        sql = f"""
                            INSERT INTO {table}
                            ({", ".join(columns)})
                            VALUES ({placeholders})
                        """

                        cursor.execute(
                            sql,
                            tuple(
                                values[column]
                                for column in columns
                            ),
                        )

                        inserted += 1

                        continue

                    # --------------------------
                    # UPDATE
                    # --------------------------

                    update_values = dict(values)

                    update_values.pop(
                        primary_key,
                        None,
                    )

                    if not update_values:
                        continue

                    assignments = ", ".join(
                        f"{column}=?"
                        for column in update_values
                    )

                    sql = f"""
                        UPDATE {table}
                        SET {assignments}
                        WHERE {primary_key}=?
                    """

                    parameters = list(
                        update_values.values()
                    )

                    parameters.append(record_id)

                    cursor.execute(
                        sql,
                        tuple(parameters),
                    )

                    if cursor.rowcount:

                        updated += 1

                    else:

                        columns = list(values.keys())

                        placeholders = ",".join(
                            "?"
                            for _ in columns
                        )

                        insert_sql = f"""
                            INSERT INTO {table}
                            ({", ".join(columns)})
                            VALUES ({placeholders})
                        """

                        cursor.execute(
                            insert_sql,
                            tuple(
                                values[column]
                                for column in columns
                            ),
                        )

                        inserted += 1

            finally:

                cursor.close()

        return inserted, updated

    # ==================================================
    # Bulk Read Helpers
    # ==================================================

    def fetch_by_ids(
        self,
        table: str,
        ids: Sequence[Any],
        primary_key: str = "id",
    ) -> list[dict[str, Any]]:
        """
        Fetch multiple rows by IDs.
        """

        self._validate_table(table)
        self._validate_column(primary_key)

        if not ids:
            return []

        placeholders = ",".join(
            "?"
            for _ in ids
        )

        sql = f"""
            SELECT *
            FROM {table}
            WHERE {primary_key}
            IN ({placeholders})
        """

        return self.fetch_all(
            sql,
            tuple(ids),
        )

    # --------------------------------------------------

    def bulk_exists(
        self,
        table: str,
        column: str,
        values: Sequence[Any],
    ) -> dict[Any, bool]:
        """
        Return existence map.
        """

        existing = self.existing_values(
            table,
            column,
            values,
        )

        return {
            value: value in existing
            for value in values
        }

    # ==================================================
    # Bulk Utilities
    # ==================================================

    @staticmethod
    def chunk(
        items: Sequence[Any],
        chunk_size: int = 500,
    ) -> list[list[Any]]:
        """
        Split sequence into chunks.
        """

        if chunk_size <= 0:
            raise ValueError(
                "chunk_size must be > 0"
            )

        return [

            list(
                items[index:index + chunk_size]
            )

            for index in range(
                0,
                len(items),
                chunk_size,
            )

        ]

    # --------------------------------------------------

    @staticmethod
    def deduplicate(
        rows: Sequence[Mapping[str, Any]],
        key: str,
    ) -> list[dict[str, Any]]:
        """
        Remove duplicate dictionaries
        using the supplied key.
        """

        seen = set()

        result = []

        for row in rows:

            value = row.get(key)

            if value in seen:
                continue

            seen.add(value)

            result.append(dict(row))

        return result

    # --------------------------------------------------

    @staticmethod
    def filter_missing_keys(
        rows: Sequence[Mapping[str, Any]],
        key: str,
    ) -> list[dict[str, Any]]:
        """
        Remove rows missing the key.
        """

        return [
            dict(row)
            for row in rows
            if row.get(key) is not None
        ]

    # ==================================================
    # Repository Information
    # ==================================================

    @property
    def repository_name(
        self,
    ) -> str:
        return "BulkRepository"

    # --------------------------------------------------

    def __repr__(
        self,
    ) -> str:

        return (
            f"{self.repository_name}()"
        )
