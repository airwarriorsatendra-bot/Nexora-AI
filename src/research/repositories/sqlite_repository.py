"""SQLite-specific schema lifecycle support for research repositories."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path
from typing import Generic, TypeVar

from src.research.repositories.base_repository import BaseRepository

__all__ = ["SQLiteRepository"]

T = TypeVar("T")


class SQLiteRepository(BaseRepository[T], Generic[T], ABC):
    """Adds safe, idempotent schema initialization to ``BaseRepository``."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        max_retries: int = BaseRepository.DEFAULT_MAX_RETRIES,
        retry_delay: float = BaseRepository.DEFAULT_RETRY_DELAY,
    ) -> None:
        super().__init__(
            database_path,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        self._schema_ready = False
        self._schema_lock = asyncio.Lock()

    @property
    @abstractmethod
    def schema_statements(self) -> Sequence[str]:
        """DDL statements required by the concrete repository."""

    async def initialize(self) -> None:
        """Create the repository schema exactly once per repository instance."""
        if self._schema_ready:
            return
        async with self._schema_lock:
            if self._schema_ready:
                return
            for statement in self.schema_statements:
                await self._execute(statement, operation_name="initialize schema")
            self._schema_ready = True
