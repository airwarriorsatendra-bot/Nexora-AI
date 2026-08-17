"""
==========================================================
NEXORA AI
Shared Data Models
==========================================================

Shared dataclasses used across:

- Research Agent
- Manager Agent
- Website Analyzer
- Database Repositories
- Dashboard
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


# ==========================================================
# Prospect Model
# ==========================================================

@dataclass(slots=True)
class Prospect:
    """
    Represents a backlink opportunity discovered by Nexora AI.
    """

    # Identity
    id: Optional[int] = None

    title: str = ""
    url: str = ""

    # Website
    description: str = ""
    category: str = ""

    # Contact
    emails: List[str] = field(default_factory=list)
    phone_numbers: List[str] = field(default_factory=list)

    contact_page: str = ""
    about_page: str = ""
    write_for_us: str = ""

    social_links: List[str] = field(default_factory=list)

    # AI Analysis
    niche: str = ""

    summary: str = ""

    accepts_guest_posts: bool = False

    backlink_value: str = ""

    reason: str = ""

    # AI Score
    priority_score: int = 0

    priority: str = "Unknown"

    # CRM
    status: str = "New"

    notes: str = ""

    # Metadata
    source: str = "serper"

    created_at: Optional[datetime] = None

    last_scanned: Optional[datetime] = None


# ==========================================================
# Outreach Record
# ==========================================================

@dataclass(slots=True)
class OutreachRecord:

    id: Optional[int] = None

    website: str = ""

    email: str = ""

    subject: str = ""

    body: str = ""

    model: str = ""

    created_at: Optional[datetime] = None


# ==========================================================
# Dashboard Metrics
# ==========================================================

@dataclass(slots=True)
class DashboardMetrics:

    total: int = 0

    high_priority: int = 0

    with_email: int = 0

    with_phone: int = 0

    average_score: float = 0.0


# ==========================================================
# Search Filters
# ==========================================================

@dataclass(slots=True)
class SearchFilters:

    keyword: str = ""

    category: str = ""

    minimum_score: int = 0

    status: str = ""


# ==========================================================
# Bulk Import Result
# ==========================================================

@dataclass(slots=True)
class BulkResult:

    inserted: int = 0

    updated: int = 0

    skipped: int = 0

    failed: int = 0

    total: int = 0