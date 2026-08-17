"""
src/research/domain/prospect.py

Enterprise Prospect Domain Model

Represents a discovered website during research.

Responsibilities
----------------
• Website identity
• Contact information
• Social profiles
• SEO metrics
• AI analysis
• Business metadata

This entity is immutable and validated using Pydantic v2.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Final
from uuid import UUID, uuid4

from pydantic import (
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
)

from src.shared.base.base_model import NexoraModel


class Prospect(NexoraModel):
    """
    Enterprise domain entity representing a discovered prospect.

    A Prospect contains all collected intelligence about a website
    discovered during the research process.

    This model is shared by:

    • Research Service
    • SEO Analysis
    • Backlink Intelligence
    • Outreach
    • Local SEO
    • Dashboard
    • API

    Notes
    -----
    This model intentionally contains only domain data and
    domain-related computed properties.

    Heavy business logic belongs in the service layer.
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

    prospect_id: UUID = Field(
        default_factory=uuid4,
        description="Unique prospect identifier.",
    )

    # ==========================================================
    # Website Information
    # ==========================================================

    domain: str = Field(
        min_length=1,
        max_length=255,
        description="Website domain.",
    )

    url: HttpUrl = Field(
        description="Canonical website URL.",
    )

    title: str = Field(
        default="",
        max_length=500,
        description="Website title.",
    )

    description: str = Field(
        default="",
        max_length=5000,
        description="Website description.",
    )

    category: str = Field(
        default="",
        max_length=200,
        description="Business category.",
    )

    # ==========================================================
    # Contact Information
    # ==========================================================

    email: EmailStr | None = Field(
        default=None,
        description="Primary contact email.",
    )

    phone: str | None = Field(
        default=None,
        max_length=50,
        description="Primary phone number.",
    )

    contact_page: HttpUrl | None = Field(
        default=None,
        description="Contact page URL.",
    )

    about_page: HttpUrl | None = Field(
        default=None,
        description="About page URL.",
    )

    # ==========================================================
    # Social Profiles
    # ==========================================================

    facebook: HttpUrl | None = None

    instagram: HttpUrl | None = None

    linkedin: HttpUrl | None = None

    twitter: HttpUrl | None = None

    youtube: HttpUrl | None = None
    # ==========================================================
    # SEO Metrics
    # ==========================================================

    domain_authority: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Moz Domain Authority (0-100).",
    )

    page_authority: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Moz Page Authority (0-100).",
    )

    domain_rating: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Ahrefs Domain Rating (0-100).",
    )

    spam_score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Moz Spam Score (0-100).",
    )

    organic_traffic: int | None = Field(
        default=None,
        ge=0,
        description="Estimated monthly organic traffic.",
    )

    backlinks: int | None = Field(
        default=None,
        ge=0,
        description="Estimated backlink count.",
    )

    # ==========================================================
    # AI Intelligence
    # ==========================================================

    ai_score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Overall AI quality score.",
    )

    guest_post_probability: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Likelihood that the website accepts guest posts.",
    )

    ai_summary: str | None = Field(
        default=None,
        max_length=10000,
        description="AI-generated research summary.",
    )

    priority: str | None = Field(
        default=None,
        max_length=30,
        description="Priority assigned by the research pipeline.",
    )

    # ==========================================================
    # Research Metadata
    # ==========================================================

    discovered_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when this prospect was discovered.",
    )

    provider: str = Field(
        default="",
        max_length=100,
        description="Provider that discovered this prospect.",
    )

    research_query: str = Field(
        default="",
        max_length=1000,
        description="Original search query that produced this prospect.",
    )
    # ==========================================================
    # Computed Properties
    # ==========================================================

    @property
    def has_contact_information(self) -> bool:
        """
        Returns True if at least one contact method exists.
        """
        return any(
            (
                self.email,
                self.phone,
                self.contact_page,
            )
        )

    @property
    def has_social_profiles(self) -> bool:
        """
        Returns True if any social profile is available.
        """
        return any(
            (
                self.facebook,
                self.instagram,
                self.linkedin,
                self.twitter,
                self.youtube,
            )
        )

    @property
    def seo_metrics_available(self) -> bool:
        """
        Returns True if at least one SEO metric exists.
        """
        return any(
            (
                self.domain_authority is not None,
                self.page_authority is not None,
                self.domain_rating is not None,
                self.spam_score is not None,
                self.organic_traffic is not None,
                self.backlinks is not None,
            )
        )

    @property
    def ai_analysis_available(self) -> bool:
        """
        Returns True if AI enrichment has been completed.
        """
        return any(
            (
                self.ai_score is not None,
                self.ai_summary,
                self.guest_post_probability is not None,
            )
        )

    @property
    def is_contactable(self) -> bool:
        """
        Indicates whether outreach can be initiated.
        """
        return self.has_contact_information

    @property
    def display_name(self) -> str:
        """
        Human-readable prospect name.
        """
        return self.title if self.title else self.domain

    @property
    def outreach_ready(self) -> bool:
        """
        Returns True when the prospect has enough information
        for an outreach campaign.
        """
        return (
            self.has_contact_information
            and self.seo_metrics_available
        )

    @property
    def profile_completeness(self) -> float:
        """
        Calculates an approximate completeness score (0-100).

        This score is intended for dashboard display only and
        should not be used as a ranking algorithm.
        """

        checks = (
            self.domain,
            self.url,
            self.title,
            self.description,
            self.category,
            self.email,
            self.phone,
            self.contact_page,
            self.about_page,
            self.facebook,
            self.instagram,
            self.linkedin,
            self.twitter,
            self.youtube,
            self.domain_authority,
            self.page_authority,
            self.domain_rating,
            self.spam_score,
            self.organic_traffic,
            self.backlinks,
            self.ai_score,
            self.ai_summary,
            self.provider,
        )

        completed = sum(value is not None and value != "" for value in checks)

        return round((completed / len(checks)) * 100.0, 2)

    # ==========================================================
    # Business Methods
    # ==========================================================

    def has_email(self) -> bool:
        """
        Returns True if an email address exists.
        """
        return self.email is not None

    def has_phone(self) -> bool:
        """
        Returns True if a phone number exists.
        """
        return self.phone is not None

    def has_about_page(self) -> bool:
        """
        Returns True if an About page was discovered.
        """
        return self.about_page is not None

    def has_contact_page(self) -> bool:
        """
        Returns True if a Contact page was discovered.
        """
        return self.contact_page is not None

    def has_backlink_metrics(self) -> bool:
        """
        Returns True if backlink metrics are available.
        """
        return any(
            (
                self.domain_authority is not None,
                self.page_authority is not None,
                self.domain_rating is not None,
                self.backlinks is not None,
            )
        )

    def has_ai_summary(self) -> bool:
        """
        Returns True if an AI summary exists.
        """
        return bool(self.ai_summary)

    def can_be_ranked(self) -> bool:
        """
        Determines whether this prospect contains enough
        information for ranking algorithms.
        """
        return (
            self.seo_metrics_available
            and self.ai_analysis_available
        )

    def supports_outreach(self) -> bool:
        """
        Determines whether the prospect is suitable for
        automated outreach.
        """
        return self.has_contact_information
    # ==========================================================
    # Equality & Representation
    # ==========================================================

    def __str__(self) -> str:
        """
        Human-readable representation.
        """
        return self.display_name

    def __repr__(self) -> str:
        """
        Developer-friendly representation.
        """
        return (
            f"{self.__class__.__name__}("
            f"domain={self.domain!r}, "
            f"url={str(self.url)!r}, "
            f"provider={self.provider!r})"
        )

    # ==========================================================
    # Export Helpers
    # ==========================================================

    def contact_summary(self) -> dict[str, str]:
        """
        Returns all available contact information.

        Useful for outreach services.
        """
        summary: dict[str, str] = {}

        if self.email:
            summary["email"] = str(self.email)

        if self.phone:
            summary["phone"] = self.phone

        if self.contact_page:
            summary["contact_page"] = str(self.contact_page)

        return summary

    def social_summary(self) -> dict[str, str]:
        """
        Returns discovered social profiles.
        """

        profiles: dict[str, str] = {}

        if self.facebook:
            profiles["facebook"] = str(self.facebook)

        if self.instagram:
            profiles["instagram"] = str(self.instagram)

        if self.linkedin:
            profiles["linkedin"] = str(self.linkedin)

        if self.twitter:
            profiles["twitter"] = str(self.twitter)

        if self.youtube:
            profiles["youtube"] = str(self.youtube)

        return profiles

    def seo_summary(self) -> dict[str, float | int]:
        """
        Returns available SEO metrics.
        """

        metrics: dict[str, float | int] = {}

        if self.domain_authority is not None:
            metrics["domain_authority"] = self.domain_authority

        if self.page_authority is not None:
            metrics["page_authority"] = self.page_authority

        if self.domain_rating is not None:
            metrics["domain_rating"] = self.domain_rating

        if self.spam_score is not None:
            metrics["spam_score"] = self.spam_score

        if self.organic_traffic is not None:
            metrics["organic_traffic"] = self.organic_traffic

        if self.backlinks is not None:
            metrics["backlinks"] = self.backlinks

        return metrics

    # ==========================================================
    # Convenience Flags
    # ==========================================================

    @property
    def is_high_quality(self) -> bool:
        """
        Indicates whether the prospect meets a basic quality threshold.

        This is a lightweight convenience property and should not
        replace dedicated scoring services.
        """

        return (
            self.domain_authority is not None
            and self.domain_authority >= 40
            and self.spam_score is not None
            and self.spam_score <= 10
        )

    @property
    def is_enriched(self) -> bool:
        """
        Returns True if SEO and AI enrichment have completed.
        """

        return (
            self.seo_metrics_available
            and self.ai_analysis_available
        )
