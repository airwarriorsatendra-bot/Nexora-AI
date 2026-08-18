"""
src/core/enums.py

Shared enumerations for Nexora AI.

This module contains platform-wide enums used across the application.
All enums inherit from `str` and `Enum` to ensure:

- JSON serialization compatibility
- Pydantic v2 compatibility
- SQLite/PostgreSQL compatibility
- Consistent string comparisons
- Improved type safety
"""

from enum import Enum


# ============================================================================
# Research
# ============================================================================

class ResearchStatus(str, Enum):
    """Lifecycle state of a research session."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ResearchPhase(str, Enum):
    """Current execution phase of a research workflow."""

    INITIALIZING = "initializing"
    GENERATING_QUERIES = "generating_queries"
    SEARCHING = "searching"
    CRAWLING = "crawling"
    AI_ANALYSIS = "ai_analysis"
    SAVING_RESULTS = "saving_results"
    COMPLETED = "completed"


class ResearchMode(str, Enum):
    """Supported research modes."""

    GUEST_POST = "guest_post"
    DIRECTORY = "directory"
    RESOURCE_PAGE = "resource_page"
    BLOG = "blog"
    BUSINESS = "business"
    LOCAL = "local"
    CUSTOM = "custom"

    # Future
    BROKEN_LINK = "broken_link"
    COMPETITOR = "competitor"
    LINK_INSERTION = "link_insertion"
    PODCAST = "podcast"
    NEWS = "news"
    FORUM = "forum"
    SAAS = "saas"


# ============================================================================
# Search
# ============================================================================

class SearchProvider(str, Enum):
    """Supported search providers."""

    TAVILY = "tavily"
    SERPER = "serper"
    BRAVE = "brave"
    GOOGLE_CSE = "google_cse"
    BING = "bing"
    PERPLEXITY = "perplexity"

    # Future
    EXA = "exa"
    SERPAPI = "serpapi"
    FIRECRAWL = "firecrawl"


# ============================================================================
# AI
# ============================================================================

class AIProvider(str, Enum):
    """Supported AI providers."""

    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"
    NVIDIA = "nvidia"
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"


# ============================================================================
# SEO Metrics
# ============================================================================

class AuthorityProvider(str, Enum):
    """Supported SEO authority providers."""

    MOZ = "moz"
    AHREFS = "ahrefs"
    SEMRUSH = "semrush"
    MAJESTIC = "majestic"


# ============================================================================
# Backlinks
# ============================================================================

class BacklinkVerificationStatus(str, Enum):
    """Observed lifecycle state of a candidate backlink."""

    DISCOVERED = "discovered"
    VERIFIED = "verified"
    LOST = "lost"
    UNREACHABLE = "unreachable"


class BacklinkOpportunityStatus(str, Enum):
    """Workflow state of a backlink opportunity, separate from outreach."""

    NEW = "new"
    QUALIFIED = "qualified"
    IGNORED = "ignored"
    OUTREACH_READY = "outreach_ready"


class BacklinkOpportunityType(str, Enum):
    """Deterministic opportunity categories inferred from available evidence."""

    GUEST_POST = "guest_post"
    RESOURCE_PAGE = "resource_page"
    DIRECTORY = "directory"
    COMPETITOR_LINK = "competitor_link"
    BROKEN_LINK = "broken_link"
    LISTICLE = "listicle"
    BLOG = "blog"
    NEWS = "news"
    PARTNER = "partner"
    OTHER = "other"


class LinkAttribute(str, Enum):
    """Observable HTML rel attributes on a verified link."""

    FOLLOW = "follow"
    NOFOLLOW = "nofollow"
    SPONSORED = "sponsored"
    UGC = "ugc"


# ============================================================================
# Outreach
# ============================================================================

class CampaignStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class CampaignObjective(str, Enum):
    BACKLINK_OUTREACH = "backlink_outreach"
    GUEST_POST = "guest_post"
    RESOURCE_PAGE = "resource_page"
    BROKEN_LINK = "broken_link"
    PARTNERSHIP = "partnership"
    GENERAL = "general"


class RecipientStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    SENT = "sent"
    REPLIED = "replied"
    SUPPRESSED = "suppressed"
    BOUNCED = "bounced"
    REMOVED = "removed"


class MessageStatus(str, Enum):
    PREPARED = "prepared"
    DRY_RUN = "dry_run"
    SENT = "sent"
    FAILED = "failed"
    QUEUED = "queued"
    SENDING = "sending"
    BOUNCED = "bounced"
    REPLIED = "replied"
    CANCELLED = "cancelled"
    SUPPRESSED = "suppressed"
    SEND_OUTCOME_UNKNOWN = "send_outcome_unknown"


class DeliveryAttemptStatus(str, Enum):
    SIMULATED = "simulated"
    ACCEPTED = "accepted"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"


class SuppressionReason(str, Enum):
    UNSUBSCRIBE = "unsubscribe"
    MANUAL_BLOCK = "manual_block"
    HARD_BOUNCE = "hard_bounce"
    INVALID_ADDRESS = "invalid_address"
    COMPLAINT = "complaint"
    DO_NOT_CONTACT = "do_not_contact"


# ============================================================================
# Prospect Management
# ============================================================================

class ProspectStatus(str, Enum):
    """Current lifecycle state of a prospect."""

    NEW = "new"
    QUALIFIED = "qualified"
    OUTREACH_PENDING = "outreach_pending"
    CONTACTED = "contacted"
    FOLLOW_UP = "follow_up"
    REPLIED = "replied"
    NEGOTIATING = "negotiating"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ARCHIVED = "archived"


# ============================================================================
# Common
# ============================================================================

class Priority(str, Enum):
    """Priority level."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class LogLevel(str, Enum):
    """Application log level."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
