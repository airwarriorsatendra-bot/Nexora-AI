"""Async Google Custom Search JSON API adapter."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Mapping
from typing import Any

import httpx

from src.core.constants import DEFAULT_RETRY_COUNT, DEFAULT_RETRY_DELAY_SECONDS, SEARCH_TIMEOUT_SECONDS
from src.core.exceptions import ExternalAPIError
from src.core.interfaces import ISearchProvider


class GoogleCSEProvider(ISearchProvider):
    """Communicate with Google Custom Search and normalize item records."""

    _ENDPOINT = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, api_key: str, search_engine_id: str, logger: logging.Logger | None = None, http_client_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient) -> None:
        if not api_key.strip() or not search_engine_id.strip():
            raise ExternalAPIError("Google CSE API key and search engine ID are required.")
        self._api_key = api_key.strip()
        self._search_engine_id = search_engine_id.strip()
        self._logger = logger or logging.getLogger(__name__)
        self._http_client_factory = http_client_factory

    @property
    def provider_name(self) -> str:
        return "google_cse"

    async def search(self, query: str, max_results: int) -> list[dict[str, Any]]:
        normalized_query = " ".join(query.split())
        if not normalized_query or max_results < 1:
            raise ExternalAPIError("Google CSE requires a query and positive max_results.")
        data = await self._request({"key": self._api_key, "cx": self._search_engine_id, "q": normalized_query, "num": min(max_results, 10)})
        items = data.get("items", [])
        if not isinstance(items, list):
            raise ExternalAPIError("Google CSE returned an invalid items payload.")
        return [item for raw in items if isinstance(raw, Mapping) if (item := self._normalize(raw)) is not None]

    async def _request(self, params: dict[str, Any]) -> Mapping[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, DEFAULT_RETRY_COUNT + 1):
            try:
                async with self._http_client_factory(timeout=SEARCH_TIMEOUT_SECONDS) as client:
                    response = await client.get(self._ENDPOINT, params=params)
                    response.raise_for_status()
                    data = response.json()
                if not isinstance(data, Mapping):
                    raise ExternalAPIError("Google CSE returned a non-object JSON response.")
                return data
            except ExternalAPIError:
                raise
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt < DEFAULT_RETRY_COUNT:
                    await asyncio.sleep(DEFAULT_RETRY_DELAY_SECONDS * attempt)
        self._logger.error("Google CSE request failed after retries.", extra={"attempts": DEFAULT_RETRY_COUNT})
        raise ExternalAPIError("Google CSE search request failed.") from last_error

    @staticmethod
    def _normalize(result: Mapping[str, Any]) -> dict[str, Any] | None:
        url = str(result.get("link") or "").strip()
        if not url:
            return None
        return {"title": str(result.get("title") or "").strip(), "url": url, "description": str(result.get("snippet") or "").strip(), "domain": str(result.get("displayLink") or "").lower()}
