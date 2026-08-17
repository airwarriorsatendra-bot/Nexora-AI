"""
src/shared/value_objects/location.py

Location value object.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field

from src.shared.base.base_model import NexoraModel


class Location(NexoraModel):
    """
    Immutable location value object.

    Reused across Research, Local SEO,
    Google Business Profile, Analytics,
    Outreach and future mapping integrations.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    country: str = Field(
        default="",
        max_length=100,
    )

    state: str = Field(
        default="",
        max_length=100,
    )

    city: str = Field(
        default="",
        max_length=100,
    )

    postal_code: str = Field(
        default="",
        max_length=20,
    )

    address: str = Field(
        default="",
        max_length=300,
    )

    latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
    )

    longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
    )

    timezone: str = Field(
        default="",
        max_length=100,
    )

    formatted_address: str = Field(
        default="",
        max_length=500,
    )

    @property
    def has_coordinates(self) -> bool:
        """
        Returns True when latitude and longitude are available.
        """
        return (
            self.latitude is not None
            and self.longitude is not None
        )

    @property
    def display_name(self) -> str:
        """
        Human-readable location string.
        """
        parts = [
            self.city,
            self.state,
            self.country,
        ]

        return ", ".join(part for part in parts if part)