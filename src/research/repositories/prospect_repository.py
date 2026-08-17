"""SQLite implementation of the locked ``IProspectRepository`` contract."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from src.core.interfaces import IProspectRepository
from src.research.domain.prospect import Prospect
from src.research.repositories.research_repository import ResearchRepository

__all__ = ["ProspectRepository"]


class ProspectRepository(ResearchRepository, IProspectRepository):
    """Persist research prospects independently from the legacy dashboard schema."""

    TABLE_NAME = "research_prospects"
    COLUMNS = (
        "prospect_id", "domain", "url", "title", "description", "category",
        "email", "phone", "contact_page", "about_page", "facebook", "instagram",
        "linkedin", "twitter", "youtube", "domain_authority", "page_authority",
        "domain_rating", "spam_score", "organic_traffic", "backlinks", "ai_score",
        "guest_post_probability", "ai_summary", "priority", "discovered_at",
        "provider", "research_query",
    )

    @property
    def schema_statements(self) -> Sequence[str]:
        return (
            """
            CREATE TABLE IF NOT EXISTS research_prospects (
                prospect_id TEXT PRIMARY KEY,
                domain TEXT NOT NULL UNIQUE COLLATE NOCASE,
                url TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '', description TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT '', email TEXT, phone TEXT,
                contact_page TEXT, about_page TEXT, facebook TEXT, instagram TEXT,
                linkedin TEXT, twitter TEXT, youtube TEXT,
                domain_authority REAL, page_authority REAL, domain_rating REAL,
                spam_score REAL, organic_traffic INTEGER, backlinks INTEGER,
                ai_score REAL, guest_post_probability REAL, ai_summary TEXT,
                priority TEXT, discovered_at TEXT NOT NULL, provider TEXT NOT NULL DEFAULT '',
                research_query TEXT NOT NULL DEFAULT ''
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_research_prospects_domain ON research_prospects(domain)",
            "CREATE INDEX IF NOT EXISTS idx_research_prospects_discovered_at ON research_prospects(discovered_at DESC)",
        )

    @property
    def _upsert_sql(self) -> str:
        columns = ", ".join(self.COLUMNS)
        placeholders = ", ".join("?" for _ in self.COLUMNS)
        updates = ", ".join(
            f"{column}=excluded.{column}"
            for column in self.COLUMNS
            if column != "prospect_id"
        )
        return (
            f"INSERT INTO {self.TABLE_NAME} ({columns}) VALUES ({placeholders}) "
            f"ON CONFLICT(domain) DO UPDATE SET {updates}"
        )

    def _parameters(self, prospect: Prospect) -> tuple[Any, ...]:
        data = self.serialize_prospect(prospect)
        return tuple(data[column] for column in self.COLUMNS)

    async def save(self, prospect: Prospect) -> Prospect:
        await self.initialize()
        await self._execute(self._upsert_sql, self._parameters(prospect), operation_name="save prospect")
        return await self.find_by_domain(prospect.domain) or prospect

    async def save_many(self, prospects: Iterable[Prospect]) -> int:
        items = list(prospects)
        if not items:
            return 0
        await self.initialize()
        return await self._executemany(
            self._upsert_sql,
            [self._parameters(prospect) for prospect in items],
            operation_name="save prospects",
        )

    async def update(self, prospect: Prospect) -> Prospect:
        return await self.save(prospect)

    async def delete(self, prospect_id: Any) -> bool:
        await self.initialize()
        affected = await self._execute(
            f"DELETE FROM {self.TABLE_NAME} WHERE prospect_id = ?",
            (str(prospect_id),),
            operation_name="delete prospect",
        )
        return affected > 0

    async def exists_by_domain(self, domain: str) -> bool:
        await self.initialize()
        value = await self._fetch_value(
            f"SELECT 1 FROM {self.TABLE_NAME} WHERE domain = ? LIMIT 1",
            (self.normalize_domain(domain),),
            operation_name="check prospect domain",
        )
        return value is not None

    async def find_by_domain(self, domain: str) -> Prospect | None:
        await self.initialize()
        row = await self._fetchone(
            f"SELECT * FROM {self.TABLE_NAME} WHERE domain = ? LIMIT 1",
            (self.normalize_domain(domain),),
            operation_name="find prospect by domain",
        )
        return None if row is None else self.deserialize_prospect(row)

    async def find_all(self) -> list[Prospect]:
        await self.initialize()
        rows = await self._fetchall(
            f"SELECT * FROM {self.TABLE_NAME} ORDER BY discovered_at DESC, domain ASC",
            operation_name="list prospects",
        )
        return [self.deserialize_prospect(row) for row in rows]
