"""
src/research/dto/response/research_progress.py

Research progress DTO.

Represents the current progress of an active research session.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field, HttpUrl

from src.core.enums import ResearchPhase
from src.shared.base.base_model import NexoraModel


class ResearchProgress(NexoraModel):
    """
    Live progress information for a running research session.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    session_id: UUID = Field(
        description="Research session identifier."
    )

    # ------------------------------------------------------------------
    # Progress
    # ------------------------------------------------------------------

    phase: ResearchPhase = Field(
        description="Current execution phase."
    )

    percentage: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Completion percentage."
    )

    processed: int = Field(
        default=0,
        ge=0
    )

    total: int = Field(
        default=0,
        ge=0
    )

    current_query: str | None = Field(
        default=None
    )

    current_url: HttpUrl | None = Field(
        default=None,
        description="Current URL being processed.",
    )

    message: str = Field(
        default=""
    )

    started_at: datetime = Field(
        description="Research start time."
    )

    updated_at: datetime = Field(
        description="Last progress update."
    )

    @property
    def remaining(self) -> int:
        """
        Remaining items.
        """
        return max(self.total - self.processed, 0)

    @property
    def is_complete(self) -> bool:
        """
        Returns True if research reached 100%.
        """
        return self.percentage >= 100.0

    @property
    def progress_ratio(self) -> float:
        """
        Returns value between 0 and 1.
        """
        return self.percentage / 100.0
