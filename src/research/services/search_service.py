"""Normalized search boundary for the research workflow."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse, urlunparse

from src.core.exceptions import SearchError
from src.core.interfaces import ISearchProvider


class SearchService:
    """Execute provider searches and return stable normalized result records."""

    def __init__(
        self,
        provider: ISearchProvider,
        logger: logging.Logger | None = None,
    ) -> None:
        self._provider = provider
        self._logger = logger or logging.getLogger(__name__)

    @property
    def service_name(self) -> str:
        """Return the service identifier."""
        return "SearchService"

    async def search(self, query: str, max_results: int) -> list[dict[str, str]]:
        """Search through the configured provider and normalize its response."""
        normalized_query = self._validate_query(query)
        if max_results < 1:
            raise SearchError("max_results must be greater than zero.")

        self._logger.info(
            "Executing search.",
            extra={
                "provider": self._provider.provider_name,
                "query": normalized_query,
                "max_results": max_results,
            },
        )
        try:
            raw_results = await self._provider.search(
                query=normalized_query,
                max_results=max_results,
            )
        except SearchError:
            raise
        except Exception as exc:
            self._logger.exception(
                "Search provider request failed.",
                extra={"provider": self._provider.provider_name},
            )
            raise SearchError(
                f"Search failed for query '{normalized_query}'."
            ) from exc

        return self._deduplicate(raw_results, max_results)

    @staticmethod
    def _validate_query(query: str) -> str:
        """Validate and normalize the provider query."""
        normalized = " ".join(query.split())
        if not normalized:
            raise SearchError("Query cannot be empty.")
        return normalized

    def _deduplicate(
        self,
        results: list[dict[str, Any]],
        max_results: int,
    ) -> list[dict[str, str]]:
        """Normalize valid result mappings and remove duplicate canonical URLs."""
        seen_urls: set[str] = set()
        normalized: list[dict[str, str]] = []
        for raw_result in results:
            if not isinstance(raw_result, Mapping):
                self._logger.warning("Ignoring non-mapping search result.")
                continue
            result = self._normalize_result(raw_result)
            if result is None or result["url"] in seen_urls:
                continue
            seen_urls.add(result["url"])
            normalized.append(result)
            if len(normalized) == max_results:
                break
        return normalized

    @staticmethod
    def _normalize_result(result: Mapping[str, Any]) -> dict[str, str] | None:
        """Map provider-specific fields to the research result shape."""
        url = str(result.get("url") or result.get("link") or "").strip()
        canonical_url = SearchService._canonical_url(url)
        if canonical_url is None:
            return None
        parsed = urlparse(canonical_url)
        return {
            "title": str(result.get("title") or "").strip(),
            "url": canonical_url,
            "description": str(
                result.get("description") or result.get("snippet") or ""
            ).strip(),
            "domain": str(result.get("domain") or parsed.hostname or "").lower(),
        }

    @staticmethod
    def _canonical_url(url: str) -> str | None:
        """Return a canonical HTTP(S) URL suitable for deduplication."""
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return None
        netloc = parsed.hostname.lower()
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        path = parsed.path or "/"
        return urlunparse((parsed.scheme.lower(), netloc, path, "", parsed.query, ""))
