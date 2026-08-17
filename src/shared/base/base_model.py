"""
src/shared/base/base_model.py

Enterprise base model used throughout Nexora AI.

All DTOs and domain models should inherit from NexoraModel.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class NexoraModel(BaseModel):
    """
    Enterprise base model.

    Provides a common configuration and helper methods for all
    DTOs, domain models and value objects.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        validate_default=True,
        use_enum_values=False,
        arbitrary_types_allowed=False,
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    def to_dict(
        self,
        *,
        exclude_none: bool = True,
        by_alias: bool = False,
    ) -> dict[str, Any]:
        """
        Convert model to dictionary.
        """
        return self.model_dump(
            exclude_none=exclude_none,
            by_alias=by_alias,
        )

    def to_json(
        self,
        *,
        exclude_none: bool = True,
        by_alias: bool = False,
        indent: int | None = None,
    ) -> str:
        """
        Convert model to JSON.
        """
        return self.model_dump_json(
            exclude_none=exclude_none,
            by_alias=by_alias,
            indent=indent,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NexoraModel":
        """
        Create model from dictionary.
        """
        return cls.model_validate(data)

    def clone(self, **updates: Any) -> "NexoraModel":
        """
        Return a validated copy of this model.
        """
        return self.model_copy(update=updates, deep=True)