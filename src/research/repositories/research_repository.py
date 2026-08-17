"""Research-domain persistence helpers shared by concrete repositories."""

from __future__ import annotations

from abc import ABC
from typing import Any

from src.research.domain.prospect import Prospect
from src.research.repositories.sqlite_repository import SQLiteRepository

__all__ = ["ResearchRepository"]


class ResearchRepository(SQLiteRepository[Prospect], ABC):
    """Maps immutable research domain prospects to and from SQLite rows."""

    @staticmethod
    def normalize_domain(domain: str) -> str:
        normalized = domain.lower().strip().removeprefix("www.").rstrip(".")
        if not normalized:
            raise ValueError("Domain cannot be empty.")
        return normalized

    @classmethod
    def serialize_prospect(cls, prospect: Prospect) -> dict[str, Any]:
        data = prospect.model_dump(mode="json")
        data["domain"] = cls.normalize_domain(prospect.domain)
        return data

    @staticmethod
    def deserialize_prospect(row: Any) -> Prospect:
        return Prospect.model_validate(dict(row))
