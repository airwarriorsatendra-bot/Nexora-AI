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
from src.outreach.providers.gmail import GmailEmailSendProvider,GmailOAuthClient,GmailReplyProvider


@dataclass(frozen=True, slots=True)
class OutreachSettings:
    database_path: Path
    max_emails_per_run: int = 10
    max_emails_per_day: int = 50
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_refresh_token: str = ""
    gmail_sender_email: str = ""
    gmail_token_uri: str = "https://oauth2.googleapis.com/token"
    gmail_live_send_enabled: bool = False
    @property
    def gmail_configured(self)->bool:return all((self.gmail_client_id,self.gmail_client_secret,self.gmail_refresh_token,self.gmail_sender_email))
    @classmethod
    def from_environment(cls, environment: dict[str, str] | None = None) -> "OutreachSettings":
        if environment is None: load_dotenv(); environment=dict(os.environ)
        value=environment.get(ENV_DATABASE_URL, "").strip()
        per_run=int(environment.get("MAX_EMAILS_PER_RUN","10"));per_day=int(environment.get("MAX_EMAILS_PER_DAY","50"))
        if per_run<1 or per_day<1 or per_run>per_day:raise ConfigurationError("Outreach send limits must be positive and per-run cannot exceed per-day.")
        gmail=(environment.get("GMAIL_CLIENT_ID","").strip(),environment.get("GMAIL_CLIENT_SECRET","").strip(),environment.get("GMAIL_REFRESH_TOKEN","").strip(),environment.get("GMAIL_SENDER_EMAIL","").strip(),environment.get("GMAIL_TOKEN_URI","https://oauth2.googleapis.com/token").strip(),environment.get("GMAIL_LIVE_SEND_ENABLED","false").strip().casefold() in {"1","true","yes","on"})
        if value.startswith("sqlite:///"): return cls(Path(value.removeprefix("sqlite:///")),per_run,per_day,*gmail)
        if value and "://" in value: raise ConfigurationError("Outreach repositories support SQLite DATABASE_URL values only.")
        return cls(Path(value) if value else Path(__file__).resolve().parents[2] / "storage" / "backlinks.db",per_run,per_day,*gmail)


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
    def __init__(self, settings: OutreachSettings, *, repository_factory=OutreachAutomationRepository, delivery_provider_factory=None,contact_provider:ContactDiscoveryProvider|None=None,verification_provider:EmailVerificationProvider|None=None,reply_provider:ReplyProvider|None=None) -> None:
        self._settings,self._repository_factory,self._delivery_factory=settings,repository_factory,delivery_provider_factory;self._contact_provider=contact_provider;self._verification_provider=verification_provider;self._reply_provider=reply_provider
    def build(self) -> OutreachApplication:
        repository=self._repository_factory(self._settings.database_path);reply=self._reply_provider
        if self._delivery_factory is not None:provider=self._delivery_factory()
        elif self._settings.gmail_configured:
            oauth=GmailOAuthClient(self._settings.gmail_client_id,self._settings.gmail_client_secret,self._settings.gmail_refresh_token,token_uri=self._settings.gmail_token_uri);provider=GmailEmailSendProvider(oauth,self._settings.gmail_sender_email,live_enabled=self._settings.gmail_live_send_enabled);reply=reply or GmailReplyProvider(oauth,self._settings.gmail_sender_email)
        else:provider=FakeDeliveryProvider()
        dependencies=tuple(x for x in (provider,self._contact_provider,self._verification_provider,reply,repository) if x is not None)
        return OutreachApplication(OutreachService(repository,provider,contact_provider=self._contact_provider,verification_provider=self._verification_provider,reply_provider=reply,max_emails_per_run=self._settings.max_emails_per_run,max_emails_per_day=self._settings.max_emails_per_day),repository,dependencies)
