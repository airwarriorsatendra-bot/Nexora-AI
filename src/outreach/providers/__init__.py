"""Replaceable delivery-provider boundary."""

from src.outreach.providers.delivery import DeliveryResult, EmailSendProvider, FakeDeliveryProvider, OutreachDeliveryProvider
from src.outreach.providers.contracts import ContactDiscoveryProvider,EmailVerificationProvider,ReplyProvider,FakeContactDiscoveryProvider,FakeEmailVerificationProvider,FakeReplyProvider

__all__ = ["DeliveryResult", "FakeDeliveryProvider", "OutreachDeliveryProvider"]
