"""
src/research/dto/response/research_statistics.py

Research statistics DTO.

Contains aggregated statistics generated during a research session.
"""

from __future__ import annotations

from datetime import timedelta

from pydantic import ConfigDict, Field

from src.shared.base.base_model import NexoraModel


class ResearchStatistics(NexoraModel):
    """
    Aggregated statistics for a completed or running research session.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    # ------------------------------------------------------------------
    # Query Statistics
    # ------------------------------------------------------------------

    queries_generated: int = Field(default=0, ge=0)

    queries_completed: int = Field(default=0, ge=0)

    # ------------------------------------------------------------------
    # Discovery Statistics
    # ------------------------------------------------------------------

    websites_discovered: int = Field(default=0, ge=0)

    websites_crawled: int = Field(default=0, ge=0)

    prospects_found: int = Field(default=0, ge=0)

    prospects_saved: int = Field(default=0, ge=0)

    duplicates_removed: int = Field(default=0, ge=0)

    failed_websites: int = Field(default=0, ge=0)

    # ------------------------------------------------------------------
    # AI Statistics
    # ------------------------------------------------------------------

    ai_processed: int = Field(default=0, ge=0)

    average_ai_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
    )

    # ------------------------------------------------------------------
    # SEO Statistics
    # ------------------------------------------------------------------

    seo_metrics_enriched: int = Field(default=0, ge=0)

    # ------------------------------------------------------------------
    # Timing
    # ------------------------------------------------------------------

    elapsed_seconds: float = Field(
        default=0.0,
        ge=0.0,
    )

    @property
    def elapsed(self) -> timedelta:
        """
        Returns elapsed execution time.
        """
        return timedelta(seconds=self.elapsed_seconds)

    @property
    def crawl_success_rate(self) -> float:
        """
        Percentage of discovered websites that were crawled.
        """
        if self.websites_discovered == 0:
            return 0.0

        return round(
            (self.websites_crawled / self.websites_discovered) * 100,
            2,
        )

    @property
    def save_success_rate(self) -> float:
        """
        Percentage of discovered prospects that were saved.
        """
        if self.prospects_found == 0:
            return 0.0

        return round(
            (self.prospects_saved / self.prospects_found) * 100,
            2,
        )

    @property
    def query_completion_rate(self) -> float:
        """
        Percentage of completed queries.
        """
        if self.queries_generated == 0:
            return 0.0

        return round(
            (self.queries_completed / self.queries_generated) * 100,
            2,
        )