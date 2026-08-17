"""Async Tavily search-provider adapter."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Mapping
from typing import Any

import httpx

from src.core.constants import (
    DEFAULT_RETRY_COUNT,
    DEFAULT_RETRY_DELAY_SECONDS,
    SEARCH_TIMEOUT_SECONDS,
)
from src.core.exceptions import ExternalAPIError
from src.core.interfaces import ISearchProvider


class TavilyProvider(ISearchProvider):
    """Communicate with Tavily's search API and normalize its result records."""

    _ENDPOINT = "https://api.tavily.com/search"

    def __init__(
        self,
        api_key: str,
        logger: logging.Logger | None = None,
        http_client_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient,
    ) -> None:
        if not api_key.strip():
            raise ExternalAPIError("Tavily API key cannot be empty.")
        self._api_key = api_key.strip()
        self._logger = logger or logging.getLogger(__name__)
        self._http_client_factory = http_client_factory

    @property
    def provider_name(self) -> str:
        """Return the configured provider identifier."""
        return "tavily"

    async def search(
        self,
        query: str,
        max_results: int,
    ) -> list[dict[str, Any]]:
        """Search Tavily and map its response to the shared search contract."""
        normalized_query = " ".join(query.split())
        if not normalized_query:
            raise ExternalAPIError("Tavily search query cannot be empty.")
        if max_results < 1:
            raise ExternalAPIError("Tavily max_results must be greater than zero.")

        payload = {
            "query": normalized_query,
            "search_depth": "advanced",
            "max_results": max_results,
        }
        response = await self._request(payload)
        results = response.get("results", [])
        if not isinstance(results, list):
            raise ExternalAPIError("Tavily returned an invalid results payload.")
        return [
            normalized
            for item in results
            if isinstance(item, Mapping)
            if (normalized := self._normalize_result(item)) is not None
        ]

    async def _request(self, payload: dict[str, Any]) -> Mapping[str, Any]:
        """Execute a retried, bounded Tavily HTTP request."""
        last_error: Exception | None = None
        for attempt in range(1, DEFAULT_RETRY_COUNT + 1):
            try:
                async with self._http_client_factory(
                    timeout=SEARCH_TIMEOUT_SECONDS,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                ) as client:
                    response = await client.post(self._ENDPOINT, json=payload)
                    response.raise_for_status()
                    data = response.json()
                if not isinstance(data, Mapping):
                    raise ExternalAPIError("Tavily returned a non-object JSON response.")
                return data
            except ExternalAPIError:
                raise
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt < DEFAULT_RETRY_COUNT:
                    await asyncio.sleep(DEFAULT_RETRY_DELAY_SECONDS * attempt)
                    continue
            except (TypeError, ValueError) as exc:
                raise ExternalAPIError("Tavily returned invalid JSON.") from exc

        self._logger.error(
            "Tavily request failed after retries.",
            extra={"attempts": DEFAULT_RETRY_COUNT},
        )
        raise ExternalAPIError("Tavily search request failed.") from last_error

    @staticmethod
    def _normalize_result(result: Mapping[str, Any]) -> dict[str, Any] | None:
        """Map a Tavily result to the shared normalized search shape."""
        url = str(result.get("url") or "").strip()
        if not url:
            return None
        return {
            "title": str(result.get("title") or "").strip(),
            "url": url,
            "description": str(result.get("content") or "").strip(),
            "domain": "",
        }
