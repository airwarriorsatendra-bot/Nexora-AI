"""
src/research/dto/request/research_request.py

Research request DTO.

Represents a validated request to start a research session.

Author: Nexora AI
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID, uuid4

from pydantic import ConfigDict, Field, field_validator

from src.core.constants import (
    DEFAULT_MAX_RESULTS,
    MAX_RESULTS_LIMIT,
    MIN_RESULTS_LIMIT,
)
from src.core.enums import (
    ResearchMode,
    SearchProvider,
)
from src.research.dto.request.research_options import ResearchOptions
from src.shared.base.base_model import NexoraModel
from src.shared.value_objects.location import Location


class ResearchRequest(NexoraModel):
    """
    Validated request for starting a research workflow.

    This DTO is immutable and should be created by the Dashboard
    before calling ResearchService.
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

    request_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this research request.",
    )

    # ------------------------------------------------------------------
    # Research
    # ------------------------------------------------------------------

    industry: Annotated[
        str,
        Field(
            min_length=2,
            max_length=200,
            description="Target industry or niche.",
        ),
    ]

    research_mode: ResearchMode = Field(
        description="Research mode."
    )

    provider: SearchProvider = Field(
        default=SearchProvider.TAVILY,
        description="Search provider."
    )

    # ------------------------------------------------------------------
    # Location
    # ------------------------------------------------------------------

    location: Location

    # ------------------------------------------------------------------
    # Options
    # ------------------------------------------------------------------

    options: ResearchOptions = Field(
        default_factory=ResearchOptions
    )

    # ------------------------------------------------------------------
    # Limits
    # ------------------------------------------------------------------

    max_results: int = Field(
        default=DEFAULT_MAX_RESULTS,
        ge=MIN_RESULTS_LIMIT,
        le=MAX_RESULTS_LIMIT,
        description="Maximum number of results to collect.",
    )

    # ------------------------------------------------------------------
    # Query Control
    # ------------------------------------------------------------------

    custom_queries: list[str] = Field(
        default_factory=list,
        description="Optional user supplied search queries.",
    )

    included_domains: list[str] = Field(
        default_factory=list,
        description="Restrict research to these domains.",
    )

    excluded_domains: list[str] = Field(
        default_factory=list,
        description="Ignore these domains.",
    )

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    tags: list[str] = Field(
        default_factory=list,
        description="Optional request tags.",
    )

    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Additional request metadata.",
    )

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("industry")
    @classmethod
    def validate_industry(cls, value: str) -> str:
        """
        Validate industry.
        """
        value = value.strip()

        if not value:
            raise ValueError("Industry cannot be empty.")

        return value

    @field_validator(
        "custom_queries",
        "included_domains",
        "excluded_domains",
        "tags",
    )
    @classmethod
    def remove_empty_values(
        cls,
        values: list[str],
    ) -> list[str]:
        """
        Remove blank values while preserving order.
        """
        cleaned: list[str] = []

        for item in values:
            item = item.strip()

            if item and item not in cleaned:
                cleaned.append(item)

        return cleaned