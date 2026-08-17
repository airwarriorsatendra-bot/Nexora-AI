"""
src/core/interfaces.py

Platform-wide contracts for Nexora AI.

These interfaces define the contracts between the application,
services, providers and repositories.

All implementations must satisfy these contracts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable

from src.research.domain.prospect import Prospect
from src.research.dto.request.research_request import ResearchRequest
from src.research.dto.response.research_progress import ResearchProgress
from src.research.dto.response.research_response import ResearchResponse


# =============================================================================
# Base Service
# =============================================================================


class IService(ABC):
    """Base interface for all services."""

    @property
    @abstractmethod
    def service_name(self) -> str:
        """Return the service name."""
        raise NotImplementedError


# =============================================================================
# Search Provider
# =============================================================================


class ISearchProvider(ABC):
    """Contract for search providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider display name."""
        raise NotImplementedError

    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int,
    ) -> list[dict[str, Any]]:
        """
        Execute a search query.

        Returns
        -------
        list[dict[str, Any]]
            Raw provider results.
        """
        raise NotImplementedError


# =============================================================================
# Query Generator
# =============================================================================


class IQueryGenerator(IService):
    """Contract for query generation."""

    @abstractmethod
    async def generate_queries(
        self,
        request: ResearchRequest,
    ) -> list[str]:
        """
        Generate research queries.
        """
        raise NotImplementedError


# =============================================================================
# Crawler
# =============================================================================


class ICrawlerService(IService):
    """Contract for crawler service."""

    @abstractmethod
    async def crawl(
        self,
        url: str,
    ) -> dict[str, Any]:
        """
        Crawl a website.
        """
        raise NotImplementedError


# =============================================================================
# AI Analysis
# =============================================================================


class IAIAnalysisService(IService):
    """Contract for AI analysis."""

    @abstractmethod
    async def analyze(
        self,
        website_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Analyze website content.
        """
        raise NotImplementedError


# =============================================================================
# Prospect Repository
# =============================================================================


class IProspectRepository(ABC):
    """Contract for prospect persistence."""

    @abstractmethod
    async def save(
        self,
        prospect: Prospect,
    ) -> Prospect:
        raise NotImplementedError

    @abstractmethod
    async def save_many(
        self,
        prospects: Iterable[Prospect],
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        prospect: Prospect,
    ) -> Prospect:
        raise NotImplementedError

    @abstractmethod
    async def delete(
        self,
        prospect_id: Any,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def exists_by_domain(
        self,
        domain: str,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def find_by_domain(
        self,
        domain: str,
    ) -> Prospect | None:
        raise NotImplementedError

    @abstractmethod
    async def find_all(self) -> list[Prospect]:
        raise NotImplementedError


# =============================================================================
# Research Service
# =============================================================================


class IResearchService(IService):
    """Contract for ResearchService."""

    @abstractmethod
    async def start_research(
        self,
        request: ResearchRequest,
    ) -> ResearchResponse:
        raise NotImplementedError

    @abstractmethod
    async def pause_research(
        self,
        session_id: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def resume_research(
        self,
        session_id: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def cancel_research(
        self,
        session_id: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_progress(
        self,
        session_id: str,
    ) -> ResearchProgress:
        raise NotImplementedError