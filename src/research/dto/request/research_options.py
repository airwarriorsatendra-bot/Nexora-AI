"""
src/research/dto/request/research_options.py

Research execution options.

This DTO controls HOW a research session executes.
It does not contain the research request itself.

Author: Nexora AI
"""

from __future__ import annotations

from pydantic import ConfigDict, Field

from src.shared.base.base_model import NexoraModel


class ResearchOptions(NexoraModel):
    """
    Configuration options that control research execution.

    This object is immutable and is intended to be embedded inside
    ResearchRequest.

    Example:
        options = ResearchOptions(
            enable_ai_analysis=True,
            enable_crawling=True,
            enable_seo_metrics=False,
        )
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    # ------------------------------------------------------------------
    # Core Features
    # ------------------------------------------------------------------

    enable_ai_analysis: bool = Field(
        default=True,
        description="Run AI analysis on crawled websites.",
    )

    enable_crawling: bool = Field(
        default=True,
        description="Crawl discovered websites.",
    )

    enable_seo_metrics: bool = Field(
        default=False,
        description="Enrich prospects with SEO metrics.",
    )

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    extract_contact_info: bool = Field(
        default=True,
        description="Extract email addresses and phone numbers.",
    )

    extract_social_links: bool = Field(
        default=True,
        description="Extract social media links.",
    )

    extract_about_page: bool = Field(
        default=True,
        description="Analyze About page if available.",
    )

    extract_contact_page: bool = Field(
        default=True,
        description="Analyze Contact page if available.",
    )

    # ------------------------------------------------------------------
    # Search Behaviour
    # ------------------------------------------------------------------

    include_subdomains: bool = Field(
        default=False,
        description="Include subdomains during research.",
    )

    follow_redirects: bool = Field(
        default=True,
        description="Follow HTTP redirects while crawling.",
    )

    deduplicate_results: bool = Field(
        default=True,
        description="Remove duplicate domains automatically.",
    )

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    save_raw_html: bool = Field(
        default=False,
        description="Persist raw HTML for future processing.",
    )

    save_search_results: bool = Field(
        default=True,
        description="Persist raw provider search results.",
    )

    # ------------------------------------------------------------------
    # AI Behaviour
    # ------------------------------------------------------------------

    generate_summary: bool = Field(
        default=True,
        description="Generate AI summary for each prospect.",
    )

    calculate_ai_score: bool = Field(
        default=True,
        description="Generate AI quality score.",
    )

    detect_guest_post_probability: bool = Field(
        default=True,
        description="Estimate guest post acceptance probability.",
    )

    # ------------------------------------------------------------------
    # Future Ready
    # ------------------------------------------------------------------

    enable_cache: bool = Field(
        default=True,
        description="Allow cached provider responses.",
    )

    enable_logging: bool = Field(
        default=True,
        description="Enable detailed research logging.",
    )