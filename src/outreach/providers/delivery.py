"""Offline-safe delivery abstraction; no live email transport is configured."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    accepted: bool
    provider_message_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    rate_limited: bool = False


class OutreachDeliveryProvider(ABC):
    """Replaceable provider boundary; implementations must never be import-active."""

    provider_name: str

    @abstractmethod
    async def send(self, *, recipient: str, subject: str, body: str, idempotency_key: str) -> DeliveryResult:
        raise NotImplementedError


# Explicit Beta 15 name; the legacy contract remains a compatibility alias.
EmailSendProvider = OutreachDeliveryProvider


class FakeDeliveryProvider(OutreachDeliveryProvider):
    """Deterministic test/development provider that never transmits email."""

    provider_name = "fake"

    def __init__(self, result: DeliveryResult | None = None) -> None:
        self._result = result
        self.calls: list[tuple[str, str]] = []

    async def send(self, *, recipient: str, subject: str, body: str, idempotency_key: str) -> DeliveryResult:
        del body, idempotency_key
        self.calls.append((recipient, subject))
        return self._result or DeliveryResult(accepted=True, provider_message_id=str(uuid4()))
