"""
src/research/dto/response/research_response.py

Standard response object returned by the ResearchService.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import ConfigDict, Field

from src.research.dto.response.research_progress import ResearchProgress
from src.research.dto.response.research_statistics import ResearchStatistics
from src.shared.base.base_model import NexoraModel


class ResearchResponse(NexoraModel):
    """
    Standard response returned by ResearchService.

    This object is used for:

    - Dashboard
    - REST API
    - CLI
    - Background Workers
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    success: bool = Field(
        description="Whether the operation succeeded."
    )

    session_id: UUID = Field(
        description="Research session identifier."
    )

    # ------------------------------------------------------------------
    # Progress
    # ------------------------------------------------------------------

    progress: ResearchProgress | None = Field(
        default=None
    )

    statistics: ResearchStatistics = Field(
        default_factory=ResearchStatistics
    )

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    results: list[Any] = Field(
        default_factory=list,
        description="Research results."
    )

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    warnings: list[str] = Field(
        default_factory=list
    )

    errors: list[str] = Field(
        default_factory=list
    )

    message: str = Field(
        default=""
    )

    @property
    def total_results(self) -> int:
        """
        Number of returned results.
        """
        return len(self.results)

    @property
    def has_errors(self) -> bool:
        """
        Returns True when response contains errors.
        """
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """
        Returns True when response contains warnings.
        """
        return len(self.warnings) > 0