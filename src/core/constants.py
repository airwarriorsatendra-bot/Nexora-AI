"""
src/core/constants.py

Application-wide constants used throughout Nexora AI.

Do not place business logic in this module.
Only immutable configuration values belong here.
"""

from __future__ import annotations

# ============================================================================
# Application
# ============================================================================

APP_NAME: str = "Nexora AI"

APP_VERSION: str = "1.0.0"

DEFAULT_LANGUAGE: str = "en"

DEFAULT_ENCODING: str = "utf-8"


# ============================================================================
# Research
# ============================================================================

DEFAULT_MAX_RESULTS: int = 100

MAX_RESULTS_LIMIT: int = 1000

MIN_RESULTS_LIMIT: int = 1

DEFAULT_BATCH_SIZE: int = 50

DEFAULT_CONCURRENT_REQUESTS: int = 5

DEFAULT_RETRY_COUNT: int = 3

DEFAULT_RETRY_DELAY_SECONDS: int = 2


# ============================================================================
# Search
# ============================================================================

SEARCH_TIMEOUT_SECONDS: int = 30

SEARCH_RATE_LIMIT_PER_MINUTE: int = 60


# ============================================================================
# Crawling
# ============================================================================

CRAWL_TIMEOUT_SECONDS: int = 30

MAX_REDIRECTS: int = 5

MAX_HTML_SIZE_BYTES: int = 5_000_000

DEFAULT_USER_AGENT: str = (
    "NexoraAI/1.0 (+https://github.com/nexora-ai)"
)


# ============================================================================
# AI
# ============================================================================

DEFAULT_AI_TEMPERATURE: float = 0.2

DEFAULT_MAX_INPUT_TOKENS: int = 8_000

DEFAULT_MAX_OUTPUT_TOKENS: int = 2_000

DEFAULT_AI_SCORE: int = 0

DEFAULT_NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"


# ============================================================================
# SEO Metrics
# ============================================================================

SEO_CACHE_DAYS: int = 30

HIGH_DOMAIN_AUTHORITY: int = 70

MEDIUM_DOMAIN_AUTHORITY: int = 40

LOW_DOMAIN_AUTHORITY: int = 20


# ============================================================================
# Pagination
# ============================================================================

DEFAULT_PAGE_SIZE: int = 25

MAX_PAGE_SIZE: int = 100


# ============================================================================
# Cache
# ============================================================================

DEFAULT_CACHE_TTL_SECONDS: int = 3600


# ============================================================================
# Logging
# ============================================================================

DEFAULT_LOGGER_NAME: str = "nexora"


# ============================================================================
# Database
# ============================================================================

DEFAULT_TRANSACTION_BATCH_SIZE: int = 100


# ============================================================================
# Environment Variables
# ============================================================================

ENV_OPENAI_API_KEY: str = "OPENAI_API_KEY"

ENV_CLAUDE_API_KEY: str = "ANTHROPIC_API_KEY"

ENV_GEMINI_API_KEY: str = "GOOGLE_API_KEY"

# Dedicated Gemini generation credential for grounded AI visibility.  This is
# intentionally distinct from the existing GOOGLE_API_KEY integration.
ENV_GROUNDED_GEMINI_API_KEY: str = "GEMINI_API_KEY"

ENV_GROQ_API_KEY: str = "GROQ_API_KEY"

ENV_NVIDIA_API_KEY: str = "NVIDIA_API_KEY"

ENV_NVIDIA_MODEL: str = "NVIDIA_MODEL"

ENV_NVIDIA_BASE_URL: str = "NVIDIA_BASE_URL"

ENV_AI_PROVIDER: str = "AI_PROVIDER"

ENV_GROUNDED_AI_PROVIDER: str = "GROUNDED_AI_PROVIDER"

ENV_GROUNDED_AI_MODEL: str = "GROUNDED_AI_MODEL"

ENV_SEARCH_PROVIDER: str = "SEARCH_PROVIDER"

ENV_TAVILY_API_KEY: str = "TAVILY_API_KEY"

ENV_BRAVE_API_KEY: str = "BRAVE_API_KEY"

ENV_SERPER_API_KEY: str = "SERPER_API_KEY"

ENV_GOOGLE_CSE_API_KEY: str = "GOOGLE_CSE_API_KEY"

ENV_GOOGLE_CSE_ID: str = "GOOGLE_CSE_ID"

ENV_PERPLEXITY_API_KEY: str = "PERPLEXITY_API_KEY"

ENV_MOZ_API_TOKEN: str = "MOZ_API_TOKEN"

ENV_MOZ_AUTHORITY_FRESHNESS_DAYS: str = "MOZ_AUTHORITY_FRESHNESS_DAYS"

# Google Search Console (OAuth refresh-token flow, read-only scope)
ENV_GSC_CLIENT_ID: str = "GSC_CLIENT_ID"
ENV_GSC_CLIENT_SECRET: str = "GSC_CLIENT_SECRET"
ENV_GSC_REFRESH_TOKEN: str = "GSC_REFRESH_TOKEN"
ENV_GA4_PROPERTY_ID: str = "GA4_PROPERTY_ID"
GA4_DATA_API_BASE_URL: str = "https://analyticsdata.googleapis.com/v1beta"
GA4_ADMIN_API_BASE_URL: str = "https://analyticsadmin.googleapis.com/v1beta"
GSC_API_BASE_URL: str = "https://www.googleapis.com/webmasters/v3"
GSC_TOKEN_URL: str = "https://oauth2.googleapis.com/token"
GSC_TIMEOUT_SECONDS: int = 30
GSC_MAX_ROW_LIMIT: int = 25_000

ENV_DATABASE_URL: str = "DATABASE_URL"

ENV_LOG_LEVEL: str = "LOG_LEVEL"
