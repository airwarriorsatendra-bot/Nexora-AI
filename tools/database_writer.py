"""Compatibility writer for dictionary-based prospect imports."""

from __future__ import annotations

from dashboard.database import prospects
from dashboard.models import Prospect


def save_prospect(site: dict) -> None:
    """Persist a legacy prospect dictionary through the canonical repository."""
    emails = site.get("Emails", "")
    phones = site.get("Phone_Numbers", site.get("Phones", ""))
    prospects.upsert(
        Prospect(
            title=site.get("Title", ""),
            url=site.get("URL", ""),
            category=site.get("Category", ""),
            description=site.get("Description", ""),
            emails=emails if isinstance(emails, list) else [emails] if emails else [],
            phone_numbers=phones if isinstance(phones, list) else [phones] if phones else [],
            contact_page=site.get("Contact_Page", ""),
            about_page=site.get("About_Page", ""),
            write_for_us=site.get("Write_For_Us", ""),
            social_links=site.get("Social_Links", []),
            accepts_guest_posts=bool(site.get("Guest_Post", False)),
            priority_score=int(site.get("Score", site.get("Priority_Score", 0)) or 0),
            priority=site.get("Priority", "Unknown"),
            status=site.get("Status", "New"),
            notes=site.get("Notes", ""),
        )
    )
