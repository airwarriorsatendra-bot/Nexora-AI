"""Async Gemini generateContent API adapter for research intelligence."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Mapping
from typing import Any

import httpx

from src.core.constants import DEFAULT_RETRY_COUNT, DEFAULT_RETRY_DELAY_SECONDS, SEARCH_TIMEOUT_SECONDS
from src.core.exceptions import ExternalAPIError


class GeminiProvider:
    """Generate structured prospect intelligence with Google Gemini."""

    _ENDPOINT_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self, api_key: str, model: str, logger: logging.Logger | None = None, http_client_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient) -> None:
        if not api_key.strip() or not model.strip():
            raise ExternalAPIError("Gemini API key and model are required.")
        self._api_key, self._model = api_key.strip(), model.strip()
        self._logger = logger or logging.getLogger(__name__)
        self._http_client_factory = http_client_factory

    async def generate(self, prompt: str) -> str:
        """Generate one JSON-formatted research analysis response."""
        if not prompt.strip():
            raise ExternalAPIError("Gemini prompt cannot be empty.")
        data = await self._request({"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}})
        candidates = data.get("candidates", [])
        if isinstance(candidates, list):
            for candidate in candidates:
                if not isinstance(candidate, Mapping):
                    continue
                content = candidate.get("content", {})
                parts = content.get("parts", []) if isinstance(content, Mapping) else []
                for part in parts if isinstance(parts, list) else []:
                    if isinstance(part, Mapping) and isinstance(part.get("text"), str):
                        return part["text"]
        raise ExternalAPIError("Gemini response did not contain text content.")

    async def _request(self, payload: dict[str, Any]) -> Mapping[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, DEFAULT_RETRY_COUNT + 1):
            try:
                async with self._http_client_factory(timeout=SEARCH_TIMEOUT_SECONDS, headers={"x-goog-api-key": self._api_key, "content-type": "application/json"}) as client:
                    response = await client.post(self._ENDPOINT_TEMPLATE.format(model=self._model), json=payload)
                    response.raise_for_status()
                    data = response.json()
                if not isinstance(data, Mapping):
                    raise ExternalAPIError("Gemini returned a non-object JSON response.")
                return data
            except ExternalAPIError:
                raise
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt < DEFAULT_RETRY_COUNT:
                    await asyncio.sleep(DEFAULT_RETRY_DELAY_SECONDS * attempt)
        self._logger.error("Gemini request failed after retries.", extra={"attempts": DEFAULT_RETRY_COUNT})
        raise ExternalAPIError("Gemini generation request failed.") from last_error
