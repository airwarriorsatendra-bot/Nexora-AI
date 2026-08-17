"""Backward-compatible helpers for saved outreach drafts."""

from dashboard.database import db
from dashboard.models import OutreachRecord
from dashboard.repositories.outreach_repository import OutreachRepository


_outreach = OutreachRepository(db)


def save_outreach(url: str, email: str) -> None:
    _outreach.create(OutreachRecord(website=url, email=url, body=email))


def get_outreach(url: str) -> str:
    records = _outreach.get_by_website(url)
    return records[0].body if records else ""


def clear_outreach(url: str) -> None:
    _outreach.delete_by_website(url)
