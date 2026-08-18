"""Async OpenAI Responses API adapter for research intelligence."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import httpx

from src.core.constants import DEFAULT_RETRY_COUNT, DEFAULT_RETRY_DELAY_SECONDS, SEARCH_TIMEOUT_SECONDS
from src.core.exceptions import ExternalAPIError


class OpenAIProvider:
    """Generate structured research intelligence through OpenAI's Responses API."""

    _ENDPOINT = "https://api.openai.com/v1/responses"

    def __init__(self, api_key: str, model: str, logger: logging.Logger | None = None, http_client_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient, sleep: Callable[[float], Awaitable[None]] = asyncio.sleep) -> None:
        if not api_key.strip() or not model.strip():
            raise ExternalAPIError("OpenAI API key and model are required.")
        self._api_key, self._model = api_key.strip(), model.strip()
        self._logger = logger or logging.getLogger(__name__)
        self._http_client_factory = http_client_factory
        self._sleep = sleep

    async def generate(self, prompt: str) -> str:
        """Generate the JSON response required by the AI analysis service."""
        if not prompt.strip():
            raise ExternalAPIError("OpenAI prompt cannot be empty.")
        data = await self._request({"model": self._model, "input": prompt, "text": {"format": {"type": "json_object"}}})
        output_text = data.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text
        output = data.get("output", [])
        if isinstance(output, list):
            for item in output:
                content = item.get("content", []) if isinstance(item, Mapping) else []
                for block in content if isinstance(content, list) else []:
                    text = block.get("text") if isinstance(block, Mapping) and block.get("type") == "output_text" else None
                    if isinstance(text, str) and text.strip():
                        return text
        raise ExternalAPIError("OpenAI response did not include output_text.")

    async def _request(self, payload: dict[str, Any]) -> Mapping[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, DEFAULT_RETRY_COUNT + 1):
            try:
                async with self._http_client_factory(timeout=SEARCH_TIMEOUT_SECONDS, headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}) as client:
                    response = await client.post(self._ENDPOINT, json=payload)
                    response.raise_for_status()
                    data = response.json()
                if not isinstance(data, Mapping):
                    raise ExternalAPIError("OpenAI returned a non-object JSON response.")
                return data
            except ExternalAPIError:
                raise
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in {429, 500, 502, 503, 504}:
                    raise ExternalAPIError("OpenAI generation request failed.") from exc
                last_error = exc
                if attempt < DEFAULT_RETRY_COUNT:
                    await self._sleep(DEFAULT_RETRY_DELAY_SECONDS * attempt)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                if attempt < DEFAULT_RETRY_COUNT:
                    await self._sleep(DEFAULT_RETRY_DELAY_SECONDS * attempt)
        self._logger.error("OpenAI request failed after retries.", extra={"attempts": DEFAULT_RETRY_COUNT})
        raise ExternalAPIError("OpenAI generation request failed.") from last_error
