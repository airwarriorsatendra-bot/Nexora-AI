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
from src.outreach.providers.contracts import ContactDiscoveryProvider,EmailVerificationProvider,ReplyProvider


@dataclass(frozen=True, slots=True)
class OutreachSettings:
    database_path: Path
    max_emails_per_run: int = 10
    max_emails_per_day: int = 50
    @classmethod
    def from_environment(cls, environment: dict[str, str] | None = None) -> "OutreachSettings":
        if environment is None: load_dotenv(); environment=dict(os.environ)
        value=environment.get(ENV_DATABASE_URL, "").strip()
        per_run=int(environment.get("MAX_EMAILS_PER_RUN","10"));per_day=int(environment.get("MAX_EMAILS_PER_DAY","50"))
        if per_run<1 or per_day<1 or per_run>per_day:raise ConfigurationError("Outreach send limits must be positive and per-run cannot exceed per-day.")
        if value.startswith("sqlite:///"): return cls(Path(value.removeprefix("sqlite:///")),per_run,per_day)
        if value and "://" in value: raise ConfigurationError("Outreach repositories support SQLite DATABASE_URL values only.")
        return cls(Path(value) if value else Path(__file__).resolve().parents[2] / "storage" / "backlinks.db",per_run,per_day)


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
    def __init__(self, settings: OutreachSettings, *, repository_factory=OutreachAutomationRepository, delivery_provider_factory=FakeDeliveryProvider,contact_provider:ContactDiscoveryProvider|None=None,verification_provider:EmailVerificationProvider|None=None,reply_provider:ReplyProvider|None=None) -> None:
        self._settings,self._repository_factory,self._delivery_factory=settings,repository_factory,delivery_provider_factory;self._contact_provider=contact_provider;self._verification_provider=verification_provider;self._reply_provider=reply_provider
    def build(self) -> OutreachApplication:
        repository=self._repository_factory(self._settings.database_path); provider=self._delivery_factory();dependencies=tuple(x for x in (provider,self._contact_provider,self._verification_provider,self._reply_provider,repository) if x is not None)
        return OutreachApplication(OutreachService(repository,provider,contact_provider=self._contact_provider,verification_provider=self._verification_provider,reply_provider=self._reply_provider,max_emails_per_run=self._settings.max_emails_per_run,max_emails_per_day=self._settings.max_emails_per_day),repository,dependencies)
