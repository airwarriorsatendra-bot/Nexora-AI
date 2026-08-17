"""
==========================================================
NEXORA AI
Enterprise Base Repository
Part 1 of 6
==========================================================

Shared repository foundation used by all repositories.

Responsibilities
----------------
- Database abstraction
- Safe query execution
- Transaction management
- Generic CRUD foundation
- JSON serialization
- UTC timestamp helpers
- Validation
- Logging

This class MUST NOT contain business logic.
"""

from __future__ import annotations

import json
import logging

from abc import ABC
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import (
    Any,
    ClassVar,
    Iterable,
    Iterator,
    Mapping,
    Sequence,
)

import pandas as pd

from dashboard.database_manager import DatabaseManager


class BaseRepository(ABC):
    """
    Enterprise repository base class.

    Every repository inherits this class.

    Child repositories only configure metadata and
    implement repository-specific methods.
    """

    # ======================================================
    # Repository Metadata
    # ======================================================

    TABLE_NAME: ClassVar[str | None] = None

    PRIMARY_KEY: ClassVar[str] = "id"

    DEFAULT_ORDER_BY: ClassVar[str] = "id"

    DEFAULT_ORDER_DIRECTION: ClassVar[str] = "ASC"

    SERIALIZED_COLUMNS: ClassVar[set[str]] = set()

    REQUIRED_COLUMNS: ClassVar[set[str]] = set()

    ALLOWED_COLUMNS: ClassVar[set[str]] = set()

    IMMUTABLE_COLUMNS: ClassVar[set[str]] = {
        "id",
    }

    # ======================================================
    # Global Allowed SQL Identifiers
    # ======================================================

    _ALLOWED_TABLES: ClassVar[set[str]] = {

        "prospects",

        "outreach",

        "email_templates",

        "settings",

        "schema_version",

    }

    _ALLOWED_COLUMNS: ClassVar[set[str]] = {

        "id",

        "title",

        "url",

        "description",

        "category",

        "emails",

        "phones",

        "contact_page",

        "about_page",

        "write_for_us",

        "social_links",

        "niche",

        "summary",

        "accepts_guest_posts",

        "backlink_value",

        "reason",

        "priority_score",

        "priority",

        "status",

        "notes",

        "source",

        "created_at",

        "last_scanned",

        "website",

        "email",

        "subject",

        "body",

        "model",

        "version",

    }

    # ======================================================
    # Constructor
    # ======================================================

    def __init__(
        self,
        db: DatabaseManager,
    ) -> None:

        self.db = db

        self.logger = logging.getLogger(
            self.__class__.__name__
        )

    # ======================================================
    # Repository Properties
    # ======================================================

    @property
    def table_name(self) -> str:

        if not self.TABLE_NAME:

            raise NotImplementedError(
                f"{self.__class__.__name__} "
                "must define TABLE_NAME."
            )

        return self.TABLE_NAME

    @property
    def primary_key(self) -> str:

        return self.PRIMARY_KEY

    @property
    def default_order(self) -> str:

        return (
            f"{self.DEFAULT_ORDER_BY} "
            f"{self.DEFAULT_ORDER_DIRECTION}"
        )

    # ======================================================
    # Validation Helpers
    # ======================================================

    @classmethod
    def _validate_table(
        cls,
        table: str,
    ) -> None:

        if table not in cls._ALLOWED_TABLES:

            raise ValueError(
                f"Invalid table name: {table}"
            )

    @classmethod
    def _validate_column(
        cls,
        column: str,
    ) -> None:

        if column not in cls._ALLOWED_COLUMNS:

            raise ValueError(
                f"Invalid column name: {column}"
            )

    @classmethod
    def _validate_identifier(
        cls,
        identifier: str,
    ) -> None:

        cls._validate_column(identifier)

    # ======================================================
    # Data Validation
    # ======================================================

    def validate_create(
        self,
        values: Mapping[str, Any],
    ) -> None:
        """
        Hook executed before INSERT.

        Child repositories override when needed.
        """

        del values

    def validate_update(
        self,
        values: Mapping[str, Any],
    ) -> None:
        """
        Hook executed before UPDATE.
        """

        del values

    def validate_delete(
        self,
        record_id: Any,
    ) -> None:
        """
        Hook executed before DELETE.
        """

        del record_id

    # ======================================================
    # Transaction Helpers
    # ======================================================

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """
        Repository transaction wrapper.

        Example

        with self.transaction():
            ...
        """

        try:

            yield

            self.db.connection.commit()

        except Exception:

            self.db.connection.rollback()

            self.logger.exception(
                "Transaction rolled back."
            )

            raise

    # ======================================================
    # Internal Utility Helpers
    # ======================================================

    @staticmethod
    def _ensure_mapping(
        values: Mapping[str, Any],
    ) -> dict[str, Any]:

        return dict(values)

    @staticmethod
    def _clean_mapping(
        values: Mapping[str, Any],
    ) -> dict[str, Any]:

        cleaned: dict[str, Any] = {}

        for key, value in values.items():

            if value is not None:

                cleaned[key] = value

        return cleaned

    def _filter_allowed_columns(
        self,
        values: Mapping[str, Any],
    ) -> dict[str, Any]:

        if not self.ALLOWED_COLUMNS:

            return dict(values)

        return {

            key: value

            for key, value in values.items()

            if key in self.ALLOWED_COLUMNS

        }

    def _remove_immutable_columns(
        self,
        values: Mapping[str, Any],
    ) -> dict[str, Any]:

        return {

            key: value

            for key, value in values.items()

            if key not in self.IMMUTABLE_COLUMNS

        }

    def _validate_required_columns(
        self,
        values: Mapping[str, Any],
    ) -> None:

        missing = [

            column

            for column in self.REQUIRED_COLUMNS

            if (
                column not in values
                or values[column] is None
            )

        ]

        if missing:

            raise ValueError(
                "Missing required fields: "
                + ", ".join(sorted(missing))
            )

    def _prepare_create_values(
        self,
        values: Mapping[str, Any],
    ) -> dict[str, Any]:

        data = self._ensure_mapping(values)

        data = self._filter_allowed_columns(data)

        self._validate_required_columns(data)

        self.validate_create(data)

        return data

    def _prepare_update_values(
        self,
        values: Mapping[str, Any],
    ) -> dict[str, Any]:

        data = self._ensure_mapping(values)

        data = self._remove_immutable_columns(data)

        data = self._filter_allowed_columns(data)

        self.validate_update(data)

        return data
    # ======================================================
    # Execute Helpers
    # ======================================================

    def execute(
        self,
        sql: str,
        params: Iterable[Any] = (),
    ) -> None:
        """
        Execute a SQL statement.
        """

        self.db.execute(
            sql,
            tuple(params),
        )

    # ------------------------------------------------------

    def executemany(
        self,
        sql: str,
        params: Iterable[Iterable[Any]],
    ) -> None:
        """
        Execute a bulk SQL statement.
        """

        self.db.executemany(
            sql,
            params,
        )

    # ------------------------------------------------------

    def bulk_insert(
        self,
        sql: str,
        rows: Iterable[Iterable[Any]],
    ) -> None:
        """
        Execute a bulk INSERT.
        """

        self.executemany(
            sql,
            rows,
        )

    # ------------------------------------------------------

    def bulk_update(
        self,
        sql: str,
        rows: Iterable[Iterable[Any]],
    ) -> None:
        """
        Execute a bulk UPDATE.
        """

        self.executemany(
            sql,
            rows,
        )

    # ======================================================
    # Fetch Helpers
    # ======================================================

    def fetch_one(
        self,
        sql: str,
        params: Iterable[Any] = (),
    ) -> dict[str, Any] | None:
        """
        Return the first matching row.
        """

        return self.db.fetch_one(
            sql,
            tuple(params),
        )

    # ------------------------------------------------------

    def fetch_all(
        self,
        sql: str,
        params: Iterable[Any] = (),
    ) -> list[dict[str, Any]]:
        """
        Return all matching rows.
        """

        return self.db.fetch_all(
            sql,
            tuple(params),
        )

    # ------------------------------------------------------

    def scalar(
        self,
        sql: str,
        params: Iterable[Any] = (),
    ) -> Any:
        """
        Return the first column of
        the first row.
        """

        return self.db.scalar(
            sql,
            tuple(params),
        )

    # ------------------------------------------------------

    def fetch_value(
        self,
        sql: str,
        params: Iterable[Any] = (),
    ) -> Any:
        """
        Readability alias.
        """

        return self.scalar(
            sql,
            tuple(params),
        )

    # ======================================================
    # DataFrame Helpers
    # ======================================================

    def dataframe(
        self,
        sql: str,
        params: Iterable[Any] = (),
    ) -> pd.DataFrame:
        """
        Return results as a pandas DataFrame.
        """

        return self.db.dataframe(
            sql,
            tuple(params),
        )

    # ======================================================
    # Generic Lookup Helpers
    # ======================================================

    def exists(
        self,
        table: str,
        column: str,
        value: Any,
    ) -> bool:
        """
        Check whether a record exists.
        """

        self._validate_table(table)
        self._validate_column(column)

        sql = f"""
            SELECT EXISTS(
                SELECT 1
                FROM {table}
                WHERE {column}=?
                LIMIT 1
            )
        """

        return bool(
            self.fetch_value(
                sql,
                (value,),
            )
        )

    # ------------------------------------------------------

    def count(
        self,
        table: str | None = None,
    ) -> int:
        """
        Count rows.
        """

        table_name = table or self.table_name

        self._validate_table(table_name)

        result = self.fetch_value(
            f"""
            SELECT COUNT(*)
            FROM {table_name}
            """
        )

        return int(result or 0)

    # ------------------------------------------------------

    def get_by_id(
        self,
        record_id: Any,
    ) -> dict[str, Any] | None:
        """
        Fetch a single record by
        primary key.
        """

        sql = f"""
            SELECT *
            FROM {self.table_name}
            WHERE {self.primary_key}=?
            LIMIT 1
        """

        return self.fetch_one(
            sql,
            (record_id,),
        )

    # ------------------------------------------------------

    def get_all(
        self,
        order_by: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch all rows.
        """

        order = order_by or self.default_order

        sql = f"""
            SELECT *
            FROM {self.table_name}
            ORDER BY {order}
        """

        return self.fetch_all(sql)

    # ------------------------------------------------------

    def get_first(
        self,
        where: str = "",
        params: Iterable[Any] = (),
    ) -> dict[str, Any] | None:
        """
        Fetch first matching row.
        """

        sql = f"""
            SELECT *
            FROM {self.table_name}
        """

        if where:

            sql += f"\nWHERE {where}"

        sql += "\nLIMIT 1"

        return self.fetch_one(
            sql,
            tuple(params),
        )

    # ------------------------------------------------------

    def get_many(
        self,
        where: str = "",
        params: Iterable[Any] = (),
        order_by: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch multiple rows.
        """

        order = order_by or self.default_order

        sql = f"""
            SELECT *
            FROM {self.table_name}
        """

        if where:

            sql += f"\nWHERE {where}"

        sql += f"\nORDER BY {order}"

        return self.fetch_all(
            sql,
            tuple(params),
        )
    # ======================================================
    # Generic CRUD Operations
    # ======================================================

    def insert(
        self,
        values: Mapping[str, Any],
    ) -> int:
        """
        Insert a record.

        Returns
        -------
        int
            Newly created primary key.
        """

        data = self._prepare_create_values(values)

        if not data:
            raise ValueError(
                "No values supplied for insert."
            )

        columns = list(data.keys())

        placeholders = ", ".join(
            "?"
            for _ in columns
        )

        sql = f"""
            INSERT INTO {self.table_name}
            ({", ".join(columns)})
            VALUES ({placeholders})
        """

        with self.transaction():

            cursor = self.db.connection.cursor()

            cursor.execute(
                sql,
                tuple(
                    data[column]
                    for column in columns
                ),
            )

            record_id = int(cursor.lastrowid)

            cursor.close()

        return record_id

    # ------------------------------------------------------

    def insert_many(
        self,
        rows: Sequence[Mapping[str, Any]],
    ) -> int:
        """
        Bulk insert records.

        Returns number of inserted rows.
        """

        if not rows:
            return 0

        prepared = [
            self._prepare_create_values(row)
            for row in rows
        ]

        columns = list(prepared[0].keys())

        placeholders = ", ".join(
            "?"
            for _ in columns
        )

        sql = f"""
            INSERT INTO {self.table_name}
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

    # ------------------------------------------------------

    def update(
        self,
        record_id: Any,
        values: Mapping[str, Any],
    ) -> bool:
        """
        Update a record.

        Returns True when updated.
        """

        self.validate_delete(record_id)

        data = self._prepare_update_values(values)

        if not data:
            return False

        assignments = ", ".join(
            f"{column}=?"
            for column in data
        )

        sql = f"""
            UPDATE {self.table_name}
            SET {assignments}
            WHERE {self.primary_key}=?
        """

        parameters = list(
            data.values()
        )

        parameters.append(record_id)

        with self.transaction():

            cursor = self.db.connection.cursor()

            cursor.execute(
                sql,
                tuple(parameters),
            )

            updated = (
                cursor.rowcount > 0
            )

            cursor.close()

        return updated

    # ------------------------------------------------------

    def update_where(
        self,
        where: str,
        where_params: Iterable[Any],
        values: Mapping[str, Any],
    ) -> int:
        """
        Generic conditional update.

        Returns affected rows.
        """

        data = self._prepare_update_values(values)

        if not data:
            return 0

        assignments = ", ".join(
            f"{column}=?"
            for column in data
        )

        sql = f"""
            UPDATE {self.table_name}
            SET {assignments}
            WHERE {where}
        """

        parameters = list(
            data.values()
        )

        parameters.extend(
            tuple(where_params)
        )

        with self.transaction():

            cursor = self.db.connection.cursor()

            cursor.execute(
                sql,
                tuple(parameters),
            )

            affected = cursor.rowcount

            cursor.close()

        return affected

    # ------------------------------------------------------

    def save(
        self,
        values: Mapping[str, Any],
    ) -> int:
        """
        Insert or update.

        If the primary key exists,
        UPDATE is executed.
        Otherwise INSERT.
        """

        data = dict(values)

        record_id = data.get(
            self.primary_key
        )

        if record_id is None:

            return self.insert(data)

        update_values = dict(data)

        update_values.pop(
            self.primary_key,
            None,
        )

        self.update(
            record_id,
            update_values,
        )

        return int(record_id)

    # ------------------------------------------------------

    def delete(
        self,
        record_id: Any,
    ) -> bool:
        """
        Delete a record.
        """

        self.validate_delete(
            record_id,
        )

        sql = f"""
            DELETE FROM {self.table_name}
            WHERE {self.primary_key}=?
        """

        with self.transaction():

            cursor = self.db.connection.cursor()

            cursor.execute(
                sql,
                (record_id,),
            )

            deleted = (
                cursor.rowcount > 0
            )

            cursor.close()

        return deleted

    # ------------------------------------------------------

    def delete_where(
        self,
        where: str,
        params: Iterable[Any] = (),
    ) -> int:
        """
        Delete matching records.
        """

        sql = f"""
            DELETE FROM {self.table_name}
            WHERE {where}
        """

        with self.transaction():

            cursor = self.db.connection.cursor()

            cursor.execute(
                sql,
                tuple(params),
            )

            affected = cursor.rowcount

            cursor.close()

        return affected

    # ------------------------------------------------------

    def truncate(self) -> None:
        """
        Delete all rows from
        the repository table.
        """

        self.execute(
            f"""
            DELETE FROM {self.table_name}
            """
        )
    # ======================================================
    # Search, Filter & Pagination Helpers
    # ======================================================

    def find_by(
        self,
        column: str,
        value: Any,
    ) -> list[dict[str, Any]]:
        """
        Return all rows where column=value.
        """

        self._validate_column(column)

        sql = f"""
            SELECT *
            FROM {self.table_name}
            WHERE {column}=?
            ORDER BY {self.default_order}
        """

        return self.fetch_all(
            sql,
            (value,),
        )

    # ------------------------------------------------------

    def find_one_by(
        self,
        column: str,
        value: Any,
    ) -> dict[str, Any] | None:
        """
        Return first row where column=value.
        """

        self._validate_column(column)

        sql = f"""
            SELECT *
            FROM {self.table_name}
            WHERE {column}=?
            LIMIT 1
        """

        return self.fetch_one(
            sql,
            (value,),
        )

    # ------------------------------------------------------

    def search(
        self,
        keyword: str,
        columns: Sequence[str],
        *,
        order_by: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Generic LIKE search.
        """

        if not columns:
            return []

        for column in columns:
            self._validate_column(column)

        conditions = " OR ".join(
            f"{column} LIKE ?"
            for column in columns
        )

        parameters = tuple(
            f"%{keyword}%"
            for _ in columns
        )

        sql = f"""
            SELECT *
            FROM {self.table_name}
            WHERE {conditions}
            ORDER BY {order_by or self.default_order}
        """

        return self.fetch_all(
            sql,
            parameters,
        )

    # ------------------------------------------------------

    def paginate(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        where: str = "",
        params: Iterable[Any] = (),
        order_by: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Generic pagination helper.
        """

        page = max(page, 1)

        page_size = max(page_size, 1)

        offset = (page - 1) * page_size

        sql = f"""
            SELECT *
            FROM {self.table_name}
        """

        if where:

            sql += f"\nWHERE {where}"

        sql += (
            f"\nORDER BY {order_by or self.default_order}"
        )

        sql += "\nLIMIT ? OFFSET ?"

        parameters = list(params)

        parameters.extend(
            [
                page_size,
                offset,
            ]
        )

        return self.fetch_all(
            sql,
            tuple(parameters),
        )

    # ------------------------------------------------------

    def count_where(
        self,
        where: str = "",
        params: Iterable[Any] = (),
    ) -> int:
        """
        Count rows matching criteria.
        """

        sql = f"""
            SELECT COUNT(*)
            FROM {self.table_name}
        """

        if where:

            sql += f"\nWHERE {where}"

        result = self.fetch_value(
            sql,
            tuple(params),
        )

        return int(result or 0)

    # ------------------------------------------------------

    def distinct(
        self,
        column: str,
    ) -> list[Any]:
        """
        Return distinct column values.
        """

        self._validate_column(column)

        sql = f"""
            SELECT DISTINCT {column}
            FROM {self.table_name}
            ORDER BY {column}
        """

        rows = self.fetch_all(sql)

        return [
            row[column]
            for row in rows
        ]

    # ------------------------------------------------------

    def bulk_delete(
        self,
        record_ids: Sequence[Any],
    ) -> int:
        """
        Delete multiple records by primary key.
        """

        if not record_ids:
            return 0

        placeholders = ",".join(
            "?"
            for _ in record_ids
        )

        sql = f"""
            DELETE FROM {self.table_name}
            WHERE {self.primary_key}
            IN ({placeholders})
        """

        with self.transaction():

            cursor = self.db.connection.cursor()

            cursor.execute(
                sql,
                tuple(record_ids),
            )

            affected = cursor.rowcount

            cursor.close()

        return affected

    # ------------------------------------------------------

    def bulk_upsert(
        self,
        rows: Sequence[Mapping[str, Any]],
    ) -> tuple[int, int]:
        """
        Insert new records and update
        existing ones.

        Returns:
            (inserted, updated)
        """

        inserted = 0

        updated = 0

        for row in rows:

            primary_key = row.get(
                self.primary_key
            )

            if (
                primary_key is None
                or self.get_by_id(primary_key) is None
            ):

                self.insert(row)

                inserted += 1

            else:

                values = dict(row)

                values.pop(
                    self.primary_key,
                    None,
                )

                self.update(
                    primary_key,
                    values,
                )

                updated += 1

        return inserted, updated

    # ------------------------------------------------------

    def dataframe_all(
        self,
        order_by: str | None = None,
    ) -> pd.DataFrame:
        """
        Return entire repository as DataFrame.
        """

        sql = f"""
            SELECT *
            FROM {self.table_name}
            ORDER BY {order_by or self.default_order}
        """

        return self.dataframe(sql)
    # ======================================================
    # JSON Serialization Helpers
    # ======================================================

    @staticmethod
    def encode_json(
        value: Any,
    ) -> str | None:
        """
        Safely serialize a Python object.
        """

        if value is None:
            return None

        return json.dumps(
            value,
            ensure_ascii=False,
        )

    # ------------------------------------------------------

    @staticmethod
    def decode_json(
        value: str | None,
        default: Any = None,
    ) -> Any:
        """
        Safely deserialize JSON.

        Never raises.
        """

        if value in (
            None,
            "",
        ):

            return [] if default is None else default

        try:

            return json.loads(value)

        except (
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ):

            return [] if default is None else default

    # ------------------------------------------------------

    def serialize_row(
        self,
        row: Mapping[str, Any],
    ) -> dict[str, Any]:
        """
        Serialize configured JSON columns
        before INSERT/UPDATE.
        """

        if not row:

            return {}

        data = dict(row)

        for column in self.SERIALIZED_COLUMNS:

            if (
                column in data
                and data[column] is not None
            ):

                data[column] = self.encode_json(
                    data[column]
                )

        return data

    # ------------------------------------------------------

    def deserialize_row(
        self,
        row: Mapping[str, Any] | None,
    ) -> dict[str, Any] | None:
        """
        Deserialize configured JSON columns.
        """

        if row is None:

            return None

        data = dict(row)

        for column in self.SERIALIZED_COLUMNS:

            if column in data:

                data[column] = self.decode_json(
                    data[column]
                )

        return data

    # ------------------------------------------------------

    def deserialize_rows(
        self,
        rows: Iterable[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Deserialize multiple rows.
        """

        return [
            self.deserialize_row(row)
            for row in rows
        ]

    # ======================================================
    # Time Helpers
    # ======================================================

    @staticmethod
    def utc_now() -> str:
        """
        Current UTC ISO timestamp.
        """

        return datetime.now(
            timezone.utc,
        ).isoformat()

    # ------------------------------------------------------

    def now(self) -> str:
        """
        Readability alias.
        """

        return self.utc_now()

    # ======================================================
    # Database Health Helpers
    # ======================================================

    def table_exists(
        self,
        table: str | None = None,
    ) -> bool:
        """
        Check table existence.
        """

        table_name = table or self.table_name

        self._validate_table(table_name)

        return self.db.table_exists(
            table_name
        )

    # ------------------------------------------------------

    def integrity_check(
        self,
    ) -> str:
        """
        Execute SQLite integrity check.
        """

        return self.db.integrity_check()

    # ------------------------------------------------------

    def optimize(
        self,
    ) -> None:
        """
        Optimize database.
        """

        self.db.optimize()

    # ------------------------------------------------------

    def backup(
        self,
        destination: str,
    ) -> None:
        """
        Create database backup.
        """

        self.db.backup(
            destination,
        )

    # ------------------------------------------------------

    @property
    def is_connected(
        self,
    ) -> bool:
        """
        Database connection status.
        """

        return self.db.is_connected

    # ======================================================
    # Logging Helpers
    # ======================================================

    def log_debug(
        self,
        message: str,
    ) -> None:

        self.logger.debug(message)

    # ------------------------------------------------------

    def log_info(
        self,
        message: str,
    ) -> None:

        self.logger.info(message)

    # ------------------------------------------------------

    def log_warning(
        self,
        message: str,
    ) -> None:

        self.logger.warning(message)

    # ------------------------------------------------------

    def log_error(
        self,
        message: str,
    ) -> None:

        self.logger.error(message)

    # ------------------------------------------------------

    def log_exception(
        self,
        message: str,
    ) -> None:

        self.logger.exception(message)

    # ======================================================
    # Extension Hooks
    # ======================================================

    def before_insert(
        self,
        values: Mapping[str, Any],
    ) -> None:
        """
        Override in child repository.
        """

        del values

    # ------------------------------------------------------

    def after_insert(
        self,
        record_id: int,
        values: Mapping[str, Any],
    ) -> None:
        """
        Override in child repository.
        """

        del record_id
        del values

    # ------------------------------------------------------

    def before_update(
        self,
        record_id: Any,
        values: Mapping[str, Any],
    ) -> None:
        """
        Override in child repository.
        """

        del record_id
        del values

    # ------------------------------------------------------

    def after_update(
        self,
        record_id: Any,
        values: Mapping[str, Any],
    ) -> None:
        """
        Override in child repository.
        """

        del record_id
        del values

    # ------------------------------------------------------

    def before_delete(
        self,
        record_id: Any,
    ) -> None:
        """
        Override in child repository.
        """

        del record_id

    # ------------------------------------------------------

    def after_delete(
        self,
        record_id: Any,
    ) -> None:
        """
        Override in child repository.
        """

        del record_id

    # ======================================================
    # Context Manager
    # ======================================================

    def __enter__(
        self,
    ) -> "BaseRepository":

        return self

    # ------------------------------------------------------

    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ) -> bool:

        return False
