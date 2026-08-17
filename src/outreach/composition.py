"""Explicit dependency composition for safe Outreach Automation."""

from __future__ import annotations

import inspect
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.core.constants import ENV_DATABASE_URL
from src.core.exceptions import ConfigurationError
from src.outreach.providers.delivery import FakeDeliveryProvider, OutreachDeliveryProvider
from src.outreach.repositories.outreach_repository import OutreachAutomationRepository
from src.outreach.services.outreach_service import OutreachService


@dataclass(frozen=True, slots=True)
class OutreachSettings:
    database_path: Path
    @classmethod
    def from_environment(cls, environment: dict[str, str] | None = None) -> "OutreachSettings":
        if environment is None: load_dotenv(); environment=dict(os.environ)
        value=environment.get(ENV_DATABASE_URL, "").strip()
        if value.startswith("sqlite:///"): return cls(Path(value.removeprefix("sqlite:///")))
        if value and "://" in value: raise ConfigurationError("Outreach repositories support SQLite DATABASE_URL values only.")
        return cls(Path(value) if value else Path(__file__).resolve().parents[2] / "storage" / "backlinks.db")


@dataclass(slots=True)
class OutreachApplication:
    service: OutreachService
    repository: OutreachAutomationRepository
    _closeables: tuple[Any,...] = ()
    _closed: bool = False
    async def aclose(self) -> None:
        if self._closed: return
        self._closed=True
        for item in reversed(self._closeables):
            close=getattr(item,"aclose",None) or getattr(item,"close",None)
            if callable(close):
                result=close()
                if inspect.isawaitable(result): await result


class OutreachComposition:
    def __init__(self, settings: OutreachSettings, *, repository_factory=OutreachAutomationRepository, delivery_provider_factory=FakeDeliveryProvider) -> None:
        self._settings,self._repository_factory,self._delivery_factory=settings,repository_factory,delivery_provider_factory
    def build(self) -> OutreachApplication:
        repository=self._repository_factory(self._settings.database_path); provider=self._delivery_factory()
        return OutreachApplication(OutreachService(repository,provider),repository,(provider,repository))
