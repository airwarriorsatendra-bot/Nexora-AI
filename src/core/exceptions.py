"""
src/core/exceptions.py

Custom exception hierarchy for Nexora AI.

All application-specific exceptions should inherit from
NexoraError.
"""

from __future__ import annotations


class NexoraError(Exception):
    """
    Base exception for the Nexora platform.
    """

    pass


# ============================================================================
# Configuration
# ============================================================================

class ConfigurationError(NexoraError):
    """Raised when application configuration is invalid."""


class ValidationError(NexoraError):
    """Raised when validation fails."""


class AuthenticationError(NexoraError):
    """Raised when authentication fails."""


class AuthorizationError(NexoraError):
    """Raised when authorization fails."""


# ============================================================================
# Infrastructure
# ============================================================================

class DatabaseError(NexoraError):
    """Database operation failed."""


class RepositoryError(DatabaseError):
    """Repository operation failed."""


# ============================================================================
# Providers
# ============================================================================

class ProviderError(NexoraError):
    """External provider error."""


class ExternalAPIError(ProviderError):
    """External API request failed."""


# ============================================================================
# Services
# ============================================================================

class ServiceError(NexoraError):
    """Base class for all service errors."""


class ResearchError(ServiceError):
    """Research workflow failed."""


class QueryGenerationError(ServiceError):
    """Query generation failed."""


class SearchError(ServiceError):
    """Search service failed."""


class CrawlError(ServiceError):
    """Crawler failed."""


class AIAnalysisError(ServiceError):
    """AI analysis failed."""


class ProspectError(ServiceError):
    """Prospect processing failed."""


class BacklinkError(ServiceError):
    """Backlink discovery or verification failed."""


class OutreachError(ServiceError):
    """Outreach campaign, message, or delivery workflow failed."""


class LocalSEOError(ServiceError):
    """Local SEO analysis failed."""


class GoogleAdsError(ServiceError):
    """Google Ads import or analysis failed."""


class MetaAdsError(ServiceError):
    """Meta Ads import or analysis failed."""


class SearchConsoleError(ServiceError):
    """Google Search Console retrieval or analysis failed."""
