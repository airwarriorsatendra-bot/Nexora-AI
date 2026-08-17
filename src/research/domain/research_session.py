"""
src/research/domain/research_session.py

Enterprise Research Session Aggregate Root

Represents one complete research execution.

Responsibilities
----------------
• Owns the complete research lifecycle
• Maintains aggregate consistency
• Tracks execution status
• Stores discovered prospects
• Collects statistics
• Records warnings/errors

This is the Aggregate Root of the Research domain.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Final
from uuid import UUID, uuid4

from pydantic import ConfigDict, Field

from src.core.enums import ResearchStatus
from src.research.domain.prospect import Prospect
from src.research.dto.request.research_request import ResearchRequest
from src.research.dto.response.research_progress import ResearchProgress
from src.research.dto.response.research_statistics import (
    ResearchStatistics,
)
from src.shared.base.base_model import NexoraModel


class ResearchSession(NexoraModel):
    """
    Aggregate Root representing one research execution.

    A ResearchSession coordinates the complete lifecycle of a
    research request from creation until completion.

    It owns:

    • Request
    • Status
    • Progress
    • Statistics
    • Prospects
    • Errors
    • Warnings

    This entity should be manipulated through aggregate methods
    instead of direct collection mutation.
    """

    model_config: Final = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
        validate_default=True,
        str_strip_whitespace=True,
        populate_by_name=True,
    )

    # ==========================================================
    # Identity
    # ==========================================================

    session_id: UUID = Field(
        default_factory=uuid4,
        description="Unique research session identifier.",
    )

    # ==========================================================
    # Request
    # ==========================================================

    request: ResearchRequest = Field(
        description="Research request associated with this session.",
    )

    # ==========================================================
    # Execution Status
    # ==========================================================

    status: ResearchStatus = Field(
        default=ResearchStatus.PENDING,
        description="Current execution status.",
    )

    progress: ResearchProgress | None = Field(
        default=None,
        description="Current execution progress.",
    )

    statistics: ResearchStatistics = Field(
        default_factory=ResearchStatistics,
        description="Execution statistics.",
    )

    # ==========================================================
    # Aggregate Collections
    # ==========================================================

    prospects: list[Prospect] = Field(
        default_factory=list,
        description="Discovered prospects.",
    )

    warnings: list[str] = Field(
        default_factory=list,
        description="Warnings generated during execution.",
    )

    errors: list[str] = Field(
        default_factory=list,
        description="Errors generated during execution.",
    )

    # ==========================================================
    # Lifecycle
    # ==========================================================

    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when execution started.",
    )

    completed_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when execution completed.",
    )

    cancelled_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when execution was cancelled.",
    )
    # ==========================================================
    # Aggregate Operations
    # ==========================================================

    def start(self) -> "ResearchSession":
        """
        Starts the research session.

        Returns:
            A new session instance in the RUNNING state.
        """

        if self.status != ResearchStatus.PENDING:
            return self

        return self.model_copy(
            update={
                "status": ResearchStatus.RUNNING,
                "started_at": datetime.now(UTC),
            }
        )

    def complete(self) -> "ResearchSession":
        """
        Marks the research session as completed.
        """

        if self.status == ResearchStatus.COMPLETED:
            return self

        return self.model_copy(
            update={
                "status": ResearchStatus.COMPLETED,
                "completed_at": datetime.now(UTC),
            }
        )

    def cancel(self) -> "ResearchSession":
        """
        Cancels the research session.
        """

        if self.status == ResearchStatus.CANCELLED:
            return self

        return self.model_copy(
            update={
                "status": ResearchStatus.CANCELLED,
                "cancelled_at": datetime.now(UTC),
            }
        )

    def fail(self, error: str) -> "ResearchSession":
        """
        Marks the session as failed and records the error.

        Args:
            error: Failure reason.
        """

        updated_errors = [*self.errors, error]

        return self.model_copy(
            update={
                "status": ResearchStatus.FAILED,
                "errors": updated_errors,
                "completed_at": datetime.now(UTC),
            }
        )

    # ==========================================================
    # Aggregate Collection Operations
    # ==========================================================

    def add_prospect(self, prospect: Prospect) -> "ResearchSession":
        """
        Returns a new session with an additional prospect.
        """

        return self.model_copy(
            update={
                "prospects": [*self.prospects, prospect]
            }
        )

    def add_warning(self, warning: str) -> "ResearchSession":
        """
        Returns a new session with an additional warning.
        """

        return self.model_copy(
            update={
                "warnings": [*self.warnings, warning]
            }
        )

    def add_error(self, error: str) -> "ResearchSession":
        """
        Returns a new session with an additional error.
        """

        return self.model_copy(
            update={
                "errors": [*self.errors, error]
            }
        )

    def update_progress(
        self,
        progress: ResearchProgress,
    ) -> "ResearchSession":
        """
        Returns a new session with updated progress.
        """

        return self.model_copy(
            update={
                "progress": progress
            }
        )

    def update_statistics(
        self,
        statistics: ResearchStatistics,
    ) -> "ResearchSession":
        """
        Returns a new session with updated statistics.
        """

        return self.model_copy(
            update={
                "statistics": statistics
            }
        )
    # ==========================================================
    # Computed Properties
    # ==========================================================

    @property
    def is_running(self) -> bool:
        """
        Returns True if the research session is currently running.
        """
        return self.status == ResearchStatus.RUNNING

    @property
    def is_completed(self) -> bool:
        """
        Returns True if the research session completed successfully.
        """
        return self.status == ResearchStatus.COMPLETED

    @property
    def is_cancelled(self) -> bool:
        """
        Returns True if the research session was cancelled.
        """
        return self.status == ResearchStatus.CANCELLED

    @property
    def is_finished(self) -> bool:
        """
        Returns True when the session has reached a terminal state.
        """

        return self.status in (
            ResearchStatus.COMPLETED,
            ResearchStatus.FAILED,
            ResearchStatus.CANCELLED,
        )

    @property
    def has_prospects(self) -> bool:
        """
        Returns True when at least one prospect exists.
        """

        return len(self.prospects) > 0

    @property
    def total_prospects(self) -> int:
        """
        Number of discovered prospects.
        """

        return len(self.prospects)

    @property
    def has_errors(self) -> bool:
        """
        Returns True when one or more errors exist.
        """

        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """
        Returns True when one or more warnings exist.
        """

        return len(self.warnings) > 0

    @property
    def duration_seconds(self) -> float:
        """
        Total execution time in seconds.

        If the session is still running, the current UTC time
        is used as the end timestamp.
        """

        end_time = (
            self.completed_at
            or self.cancelled_at
            or datetime.now(UTC)
        )

        return max(
            0.0,
            (end_time - self.started_at).total_seconds(),
        )

    @property
    def duration(self) -> str:
        """
        Human-readable execution duration.
        """

        seconds = int(self.duration_seconds)

        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        return (
            f"{hours:02}:{minutes:02}:{seconds:02}"
        )

    @property
    def success_rate(self) -> float:
        """
        Percentage of successful discoveries.

        Returns:
            Success percentage between 0 and 100.
        """

        total = self.statistics.websites_discovered

        if total == 0:
            return 0.0

        successful = self.total_prospects

        return round(
            (successful / total) * 100,
            2,
        )

    @property
    def summary(self) -> dict[str, int | str | bool]:
        """
        Lightweight dashboard summary.
        """

        return {
            "status": self.status.value,
            "prospects": self.total_prospects,
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "running": self.is_running,
            "completed": self.is_completed,
            "cancelled": self.is_cancelled,
        }
    # ==========================================================
    # Aggregate Validation
    # ==========================================================

    @property
    def is_consistent(self) -> bool:
        """
        Performs lightweight aggregate consistency checks.

        This property is intended for diagnostics and unit tests.
        """

        if (
            self.completed_at is not None
            and self.cancelled_at is not None
        ):
            return False

        if (
            self.status == ResearchStatus.COMPLETED
            and self.completed_at is None
        ):
            return False

        if (
            self.status == ResearchStatus.CANCELLED
            and self.cancelled_at is None
        ):
            return False

        if self.started_at > datetime.now(UTC):
            return False

        return True

    # ==========================================================
    # Export Helpers
    # ==========================================================

    def statistics_summary(self) -> dict[str, object]:
        """
        Returns a lightweight aggregate summary.

        Intended for dashboards, APIs and logging.
        """

        return {
            "session_id": str(self.session_id),
            "status": self.status.value,
            "prospects": self.total_prospects,
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "duration_seconds": round(
                self.duration_seconds,
                2,
            ),
        }

    # ==========================================================
    # Representation
    # ==========================================================

    def __str__(self) -> str:
        """
        Human-readable representation.
        """

        return (
            f"ResearchSession("
            f"{self.status.value}, "
            f"{self.total_prospects} prospects)"
        )

    def __repr__(self) -> str:
        """
        Developer-friendly representation.
        """

        return (
            f"{self.__class__.__name__}("
            f"session_id={self.session_id!s}, "
            f"status={self.status.value!r}, "
            f"prospects={self.total_prospects})"
        )
