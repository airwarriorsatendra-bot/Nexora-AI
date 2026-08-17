"""Async Serper Google-search provider adapter."""

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


class SerperProvider(ISearchProvider):
    """Communicate with Serper's Google Search API."""

    _ENDPOINT = "https://google.serper.dev/search"

    def __init__(
        self,
        api_key: str,
        logger: logging.Logger | None = None,
        http_client_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient,
    ) -> None:
        if not api_key.strip():
            raise ExternalAPIError("Serper API key cannot be empty.")
        self._api_key = api_key.strip()
        self._logger = logger or logging.getLogger(__name__)
        self._http_client_factory = http_client_factory

    @property
    def provider_name(self) -> str:
        """Return the configured provider identifier."""
        return "serper"

    async def search(
        self,
        query: str,
        max_results: int,
    ) -> list[dict[str, Any]]:
        """Search Serper and map organic results to the shared contract."""
        normalized_query = " ".join(query.split())
        if not normalized_query:
            raise ExternalAPIError("Serper search query cannot be empty.")
        if max_results < 1:
            raise ExternalAPIError("Serper max_results must be greater than zero.")

        response = await self._request({"q": normalized_query, "num": max_results})
        organic = response.get("organic", [])
        if not isinstance(organic, list):
            raise ExternalAPIError("Serper returned an invalid organic-results payload.")
        return [
            normalized
            for item in organic
            if isinstance(item, Mapping)
            if (normalized := self._normalize_result(item)) is not None
        ][:max_results]

    async def _request(self, payload: dict[str, Any]) -> Mapping[str, Any]:
        """Issue a retried Serper request using the documented API-key header."""
        last_error: Exception | None = None
        for attempt in range(1, DEFAULT_RETRY_COUNT + 1):
            try:
                async with self._http_client_factory(
                    timeout=SEARCH_TIMEOUT_SECONDS,
                    headers={"X-API-KEY": self._api_key, "Content-Type": "application/json"},
                ) as client:
                    response = await client.post(self._ENDPOINT, json=payload)
                    response.raise_for_status()
                    data = response.json()
                if not isinstance(data, Mapping):
                    raise ExternalAPIError("Serper returned a non-object JSON response.")
                return data
            except ExternalAPIError:
                raise
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt < DEFAULT_RETRY_COUNT:
                    await asyncio.sleep(DEFAULT_RETRY_DELAY_SECONDS * attempt)
                    continue
            except (TypeError, ValueError) as exc:
                raise ExternalAPIError("Serper returned invalid JSON.") from exc

        self._logger.error("Serper request failed after retries.", extra={"attempts": DEFAULT_RETRY_COUNT})
        raise ExternalAPIError("Serper search request failed.") from last_error

    @staticmethod
    def _normalize_result(result: Mapping[str, Any]) -> dict[str, Any] | None:
        """Map a Serper organic result to the shared normalized search shape."""
        url = str(result.get("link") or "").strip()
        if not url:
            return None
        return {
            "title": str(result.get("title") or "").strip(),
            "url": url,
            "description": str(result.get("snippet") or "").strip(),
            "domain": "",
        }
