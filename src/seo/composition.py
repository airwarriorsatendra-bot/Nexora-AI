"""Explicit composition for the SEO module using the shared crawler infrastructure."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.core.constants import ENV_DATABASE_URL
from src.research.services.crawler_service import CrawlerService
from src.seo.repositories.seo_audit_repository import SEOAuditRepository
from src.seo.services.seo_audit_service import SEOAuditService


@dataclass(frozen=True, slots=True)
class SEOSettings:
    database_path: Path

    @classmethod
    def from_environment(cls, environment: dict[str, str]) -> "SEOSettings":
        value = environment.get(ENV_DATABASE_URL, "")
        if value.startswith("sqlite:///"):
            return cls(Path(value.removeprefix("sqlite:///")))
        if value and "://" in value:
            raise ValueError("SEO repositories support SQLite DATABASE_URL values only.")
        return cls(Path(value) if value else Path(__file__).resolve().parents[2] / "storage" / "backlinks.db")


class SEOComposition:
    """Build one replaceable SEO graph with no global client ownership."""

    def __init__(self, settings: SEOSettings, *, crawler_factory=CrawlerService, repository_factory=SEOAuditRepository) -> None:
        self._settings = settings
        self._crawler_factory = crawler_factory
        self._repository_factory = repository_factory

    def build(self) -> SEOAuditService:
        crawler = self._crawler_factory()
        repository = self._repository_factory(self._settings.database_path)
        return SEOAuditService(crawler.fetch_html, repository)
