"""Shared asynchronous SQLite infrastructure for research repositories."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Generic, TypeVar

import aiosqlite

from src.core.exceptions import DatabaseError, RepositoryError

__all__ = ["BaseRepository"]

T = TypeVar("T")
R = TypeVar("R")

logger = logging.getLogger(__name__)


class BaseRepository(Generic[T], ABC):
    """Connection, transaction, retry, and query primitives for repositories."""

    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 0.10
    SQLITE_RETRY_MESSAGES = (
        "database is locked",
        "database table is locked",
        "database schema is locked",
        "database busy",
        "database is busy",
    )

    def __init__(
        self,
        database_path: str | Path,
        *,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
    ) -> None:
        path = Path(database_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path = str(path)
        self._max_retries = max(0, max_retries)
        self._retry_delay = max(0.0, retry_delay)

    async def _create_connection(self) -> aiosqlite.Connection:
        connection: aiosqlite.Connection | None = None
        try:
            connection = await aiosqlite.connect(self._database_path)
            connection.row_factory = aiosqlite.Row
            for statement in (
                "PRAGMA foreign_keys = ON",
                "PRAGMA journal_mode = WAL",
                "PRAGMA synchronous = NORMAL",
                "PRAGMA busy_timeout = 5000",
            ):
                cursor = await connection.execute(statement)
                await cursor.close()
            return connection
        except (aiosqlite.Error, OSError) as exc:
            if connection is not None:
                await connection.close()
            raise DatabaseError("Unable to establish database connection.") from exc

    @asynccontextmanager
    async def _transaction(self) -> AsyncIterator[aiosqlite.Connection]:
        connection = await self._create_connection()
        try:
            await connection.execute("BEGIN")
            yield connection
            await connection.commit()
        except Exception:
            try:
                await connection.rollback()
            except aiosqlite.Error:
                logger.exception("SQLite rollback failed.")
            raise
        finally:
            await connection.close()

    def _is_retryable_error(self, exception: Exception) -> bool:
        return isinstance(exception, aiosqlite.Error) and any(
            message in str(exception).lower()
            for message in self.SQLITE_RETRY_MESSAGES
        )

    def _map_database_exception(
        self,
        exception: Exception,
        *,
        operation: str,
    ) -> RepositoryError:
        if isinstance(exception, RepositoryError):
            return exception
        logger.exception("Repository operation failed: %s", operation)
        return RepositoryError(f"Database operation failed during '{operation}'.")

    async def _run(
        self,
        operation: Callable[[aiosqlite.Connection], Awaitable[R]],
        *,
        operation_name: str,
        transactional: bool = False,
    ) -> R:
        for attempt in range(self._max_retries + 1):
            try:
                if transactional:
                    async with self._transaction() as connection:
                        return await operation(connection)

                connection = await self._create_connection()
                try:
                    return await operation(connection)
                finally:
                    await connection.close()
            except Exception as exc:
                if attempt < self._max_retries and self._is_retryable_error(exc):
                    await asyncio.sleep(self._retry_delay * (2**attempt))
                    continue
                raise self._map_database_exception(exc, operation=operation_name) from exc
        raise RepositoryError(f"Execution engine exited unexpectedly for '{operation_name}'.")

    async def _execute(
        self,
        query: str,
        parameters: Sequence[Any] | None = None,
        *,
        operation_name: str = "execute",
    ) -> int:
        async def executor(connection: aiosqlite.Connection) -> int:
            cursor = await connection.execute(query, tuple(parameters or ()))
            try:
                return cursor.rowcount
            finally:
                await cursor.close()

        return await self._run(executor, operation_name=operation_name, transactional=True)

    async def _executemany(
        self,
        query: str,
        parameters: Sequence[Sequence[Any]],
        *,
        operation_name: str = "executemany",
    ) -> int:
        batch = list(parameters)
        if not batch:
            return 0

        async def executor(connection: aiosqlite.Connection) -> int:
            cursor = await connection.executemany(query, batch)
            try:
                return len(batch)
            finally:
                await cursor.close()

        return await self._run(executor, operation_name=operation_name, transactional=True)

    async def _fetchone(
        self,
        query: str,
        parameters: Sequence[Any] | None = None,
        *,
        operation_name: str = "fetchone",
    ) -> aiosqlite.Row | None:
        async def executor(connection: aiosqlite.Connection) -> aiosqlite.Row | None:
            cursor = await connection.execute(query, tuple(parameters or ()))
            try:
                return await cursor.fetchone()
            finally:
                await cursor.close()

        return await self._run(executor, operation_name=operation_name)

    async def _fetchall(
        self,
        query: str,
        parameters: Sequence[Any] | None = None,
        *,
        operation_name: str = "fetchall",
    ) -> list[aiosqlite.Row]:
        async def executor(connection: aiosqlite.Connection) -> list[aiosqlite.Row]:
            cursor = await connection.execute(query, tuple(parameters or ()))
            try:
                return list(await cursor.fetchall())
            finally:
                await cursor.close()

        return await self._run(executor, operation_name=operation_name)

    async def _fetch_value(
        self,
        query: str,
        parameters: Sequence[Any] | None = None,
        *,
        operation_name: str = "fetch_value",
    ) -> Any | None:
        row = await self._fetchone(query, parameters, operation_name=operation_name)
        return None if row is None else row[0]

    @property
    def database_path(self) -> str:
        return self._database_path

    @property
    def max_retries(self) -> int:
        return self._max_retries

    @property
    def retry_delay(self) -> float:
        return self._retry_delay

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(database_path={self._database_path!r})"
