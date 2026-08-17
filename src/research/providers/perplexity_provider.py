"""Async Perplexity Search API adapter."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Mapping
from typing import Any

import httpx

from src.core.constants import DEFAULT_RETRY_COUNT, DEFAULT_RETRY_DELAY_SECONDS, SEARCH_TIMEOUT_SECONDS
from src.core.exceptions import ExternalAPIError
from src.core.interfaces import ISearchProvider


class PerplexityProvider(ISearchProvider):
    """Use Perplexity's raw Search API and normalize ranked web records."""

    _ENDPOINT = "https://api.perplexity.ai/search"

    def __init__(self, api_key: str, logger: logging.Logger | None = None, http_client_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient) -> None:
        if not api_key.strip():
            raise ExternalAPIError("Perplexity API key cannot be empty.")
        self._api_key = api_key.strip()
        self._logger = logger or logging.getLogger(__name__)
        self._http_client_factory = http_client_factory

    @property
    def provider_name(self) -> str:
        return "perplexity"

    async def search(self, query: str, max_results: int) -> list[dict[str, Any]]:
        normalized_query = " ".join(query.split())
        if not normalized_query or max_results < 1:
            raise ExternalAPIError("Perplexity requires a query and positive max_results.")
        data = await self._request({"query": normalized_query, "max_results": max_results})
        results = data.get("results", [])
        if not isinstance(results, list):
            raise ExternalAPIError("Perplexity returned an invalid results payload.")
        return [item for raw in results if isinstance(raw, Mapping) if (item := self._normalize(raw)) is not None][:max_results]

    async def _request(self, payload: dict[str, Any]) -> Mapping[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, DEFAULT_RETRY_COUNT + 1):
            try:
                async with self._http_client_factory(timeout=SEARCH_TIMEOUT_SECONDS, headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}) as client:
                    response = await client.post(self._ENDPOINT, json=payload)
                    response.raise_for_status()
                    data = response.json()
                if not isinstance(data, Mapping):
                    raise ExternalAPIError("Perplexity returned a non-object JSON response.")
                return data
            except ExternalAPIError:
                raise
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt < DEFAULT_RETRY_COUNT:
                    await asyncio.sleep(DEFAULT_RETRY_DELAY_SECONDS * attempt)
        self._logger.error("Perplexity request failed after retries.", extra={"attempts": DEFAULT_RETRY_COUNT})
        raise ExternalAPIError("Perplexity search request failed.") from last_error

    @staticmethod
    def _normalize(result: Mapping[str, Any]) -> dict[str, Any] | None:
        url = str(result.get("url") or "").strip()
        if not url:
            return None
        return {"title": str(result.get("title") or "").strip(), "url": url, "description": str(result.get("snippet") or "").strip(), "domain": str(result.get("source") or "")}
