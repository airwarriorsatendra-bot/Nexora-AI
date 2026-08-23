"""Environment-backed configuration for the HTTP adapter."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from dotenv import load_dotenv

from src.core.constants import ENV_DATABASE_URL
from src.core.exceptions import ConfigurationError

DEFAULT_WEB_ORIGIN = "http://localhost:3000"


@dataclass(frozen=True, slots=True)
class APISettings:
    """Immutable API settings populated through the existing environment flow."""

    allowed_origins: tuple[str, ...]
    database_path: Path
    environment: tuple[tuple[str, str], ...] = ()

    def environment_dict(self) -> dict[str, str]:
        return dict(self.environment)

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> "APISettings":
        if environment is None:
            load_dotenv()
            environment = os.environ

        origins = tuple(
            origin.strip().rstrip("/")
            for origin in environment.get("NEXORA_ALLOWED_ORIGINS", DEFAULT_WEB_ORIGIN).split(",")
            if origin.strip()
        )
        if not origins or "*" in origins:
            raise ConfigurationError(
                "NEXORA_ALLOWED_ORIGINS must contain explicit trusted origins."
            )

        database_value = environment.get(ENV_DATABASE_URL, "").strip()
        if database_value.startswith("sqlite:///"):
            database_value = database_value.removeprefix("sqlite:///")
        elif database_value and "://" in database_value:
            raise ConfigurationError("The current Nexora API supports SQLite DATABASE_URL values only.")

        database_path = (
            Path(database_value)
            if database_value
            else Path(__file__).resolve().parents[1] / "storage" / "backlinks.db"
        )
        return cls(allowed_origins=origins, database_path=database_path, environment=tuple(environment.items()))
