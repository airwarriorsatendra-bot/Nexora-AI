"""Async Groq chat-completions adapter for research intelligence."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Mapping
from typing import Any

import httpx

from src.core.constants import DEFAULT_RETRY_COUNT, DEFAULT_RETRY_DELAY_SECONDS, SEARCH_TIMEOUT_SECONDS
from src.core.exceptions import ExternalAPIError


class GroqProvider:
    """Generate structured research intelligence through Groq's OpenAI-compatible API."""

    _ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(
        self,
        api_key: str,
        model: str,
        logger: logging.Logger | None = None,
        http_client_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient,
    ) -> None:
        if not api_key.strip() or not model.strip():
            raise ExternalAPIError("Groq API key and model are required.")
        self._api_key = api_key.strip()
        self._model = model.strip()
        self._logger = logger or logging.getLogger(__name__)
        self._http_client_factory = http_client_factory

    async def generate(self, prompt: str) -> str:
        if not prompt.strip():
            raise ExternalAPIError("Groq prompt cannot be empty.")
        data = await self._request(
            {
                "model": self._model,
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "user", "content": prompt}],
            }
        )
        choices = data.get("choices", [])
        if isinstance(choices, list):
            for choice in choices:
                message = choice.get("message") if isinstance(choice, Mapping) else None
                content = message.get("content") if isinstance(message, Mapping) else None
                if isinstance(content, str) and content.strip():
                    return content
        raise ExternalAPIError("Groq response did not contain message content.")

    async def _request(self, payload: dict[str, Any]) -> Mapping[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, DEFAULT_RETRY_COUNT + 1):
            try:
                async with self._http_client_factory(
                    timeout=SEARCH_TIMEOUT_SECONDS,
                    headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                ) as client:
                    response = await client.post(self._ENDPOINT, json=payload)
                    response.raise_for_status()
                    data = response.json()
                if not isinstance(data, Mapping):
                    raise ExternalAPIError("Groq returned a non-object JSON response.")
                return data
            except ExternalAPIError:
                raise
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt < DEFAULT_RETRY_COUNT:
                    await asyncio.sleep(DEFAULT_RETRY_DELAY_SECONDS * attempt)
        self._logger.error("Groq request failed after retries.", extra={"attempts": DEFAULT_RETRY_COUNT})
        raise ExternalAPIError("Groq generation request failed.") from last_error
