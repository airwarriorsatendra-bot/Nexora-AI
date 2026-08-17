"""Application service for prospect persistence operations."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

from src.core.exceptions import ProspectError
from src.core.interfaces import IProspectRepository
from src.research.domain.prospect import Prospect


class ProspectService:
    """Expose repository operations with domain-specific error boundaries."""

    def __init__(
        self,
        repository: IProspectRepository,
        logger: logging.Logger | None = None,
    ) -> None:
        self._repository = repository
        self._logger = logger or logging.getLogger(__name__)

    @property
    def service_name(self) -> str:
        """Return the service identifier."""
        return "ProspectService"

    async def save(self, prospect: Prospect) -> Prospect:
        """Persist one validated prospect."""
        try:
            return await self._repository.save(prospect)
        except Exception as exc:
            self._log_failure("save", domain=prospect.domain)
            raise ProspectError(
                f"Unable to save prospect '{prospect.domain}'."
            ) from exc

    async def save_many(self, prospects: Iterable[Prospect]) -> int:
        """Persist a finite collection of validated prospects in one repository call."""
        items = list(prospects)
        if not items:
            return 0
        try:
            return await self._repository.save_many(items)
        except Exception as exc:
            self._log_failure("bulk save", count=str(len(items)))
            raise ProspectError("Unable to save prospects.") from exc

    async def exists(self, domain: str) -> bool:
        """Return whether a domain already exists in persistent storage."""
        normalized = self._validate_domain(domain)
        try:
            return await self._repository.exists_by_domain(normalized)
        except Exception as exc:
            self._log_failure("duplicate check", domain=normalized)
            raise ProspectError(
                f"Unable to check prospect '{normalized}'."
            ) from exc

    async def get_by_domain(self, domain: str) -> Prospect | None:
        """Retrieve a prospect by normalized domain."""
        normalized = self._validate_domain(domain)
        try:
            return await self._repository.find_by_domain(normalized)
        except Exception as exc:
            self._log_failure("lookup", domain=normalized)
            raise ProspectError(
                f"Unable to retrieve prospect '{normalized}'."
            ) from exc

    async def delete(self, prospect_id: Any) -> bool:
        """Delete one prospect using its repository identity."""
        if prospect_id is None:
            raise ProspectError("Prospect ID cannot be null.")
        try:
            return await self._repository.delete(prospect_id)
        except Exception as exc:
            self._log_failure("delete", prospect_id=str(prospect_id))
            raise ProspectError("Unable to delete prospect.") from exc

    @staticmethod
    def _validate_domain(domain: str) -> str:
        """Normalize and validate a domain repository key."""
        normalized = domain.lower().strip().removeprefix("www.")
        if not normalized:
            raise ProspectError("Domain cannot be empty.")
        return normalized

    def _log_failure(self, operation: str, **context: str) -> None:
        """Log failed persistence operations with structured non-sensitive context."""
        self._logger.exception(
            "Prospect persistence operation failed.",
            extra={"operation": operation, **context},
        )
