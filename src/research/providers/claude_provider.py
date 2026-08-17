"""Async Anthropic Messages API adapter for research intelligence."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Mapping
from typing import Any

import httpx

from src.core.constants import DEFAULT_MAX_OUTPUT_TOKENS, DEFAULT_RETRY_COUNT, DEFAULT_RETRY_DELAY_SECONDS, SEARCH_TIMEOUT_SECONDS
from src.core.exceptions import ExternalAPIError


class ClaudeProvider:
    """Generate structured prospect intelligence with Anthropic Claude."""

    _ENDPOINT = "https://api.anthropic.com/v1/messages"
    _API_VERSION = "2023-06-01"

    def __init__(self, api_key: str, model: str, logger: logging.Logger | None = None, http_client_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient) -> None:
        if not api_key.strip() or not model.strip():
            raise ExternalAPIError("Anthropic API key and model are required.")
        self._api_key, self._model = api_key.strip(), model.strip()
        self._logger = logger or logging.getLogger(__name__)
        self._http_client_factory = http_client_factory

    async def generate(self, prompt: str) -> str:
        """Generate an analysis response from a single user prompt."""
        if not prompt.strip():
            raise ExternalAPIError("Claude prompt cannot be empty.")
        data = await self._request({"model": self._model, "max_tokens": DEFAULT_MAX_OUTPUT_TOKENS, "messages": [{"role": "user", "content": prompt}]})
        content = data.get("content", [])
        if isinstance(content, list):
            for block in content:
                if isinstance(block, Mapping) and block.get("type") == "text" and isinstance(block.get("text"), str):
                    return block["text"]
        raise ExternalAPIError("Claude response did not contain text content.")

    async def _request(self, payload: dict[str, Any]) -> Mapping[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, DEFAULT_RETRY_COUNT + 1):
            try:
                async with self._http_client_factory(timeout=SEARCH_TIMEOUT_SECONDS, headers={"x-api-key": self._api_key, "anthropic-version": self._API_VERSION, "content-type": "application/json"}) as client:
                    response = await client.post(self._ENDPOINT, json=payload)
                    response.raise_for_status()
                    data = response.json()
                if not isinstance(data, Mapping):
                    raise ExternalAPIError("Claude returned a non-object JSON response.")
                return data
            except ExternalAPIError:
                raise
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt < DEFAULT_RETRY_COUNT:
                    await asyncio.sleep(DEFAULT_RETRY_DELAY_SECONDS * attempt)
        self._logger.error("Claude request failed after retries.", extra={"attempts": DEFAULT_RETRY_COUNT})
        raise ExternalAPIError("Claude generation request failed.") from last_error
