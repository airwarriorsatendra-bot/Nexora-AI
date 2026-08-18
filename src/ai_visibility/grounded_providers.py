"""Grounded generated-response adapters for AI Visibility.

These adapters normalize only provider-supplied source metadata. They never
promote URLs found in ordinary response prose into structured citations.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import httpx

from src.ai_visibility.domain import (
    Citation,
    MonitoredPrompt,
    ProviderCapability,
    ProviderClassification,
    ProviderResponse,
)
from src.core.constants import DEFAULT_RETRY_COUNT, DEFAULT_RETRY_DELAY_SECONDS, SEARCH_TIMEOUT_SECONDS
from src.core.exceptions import ExternalAPIError


class _GroundedHTTPProvider:
    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        logger: logging.Logger | None = None,
        http_client_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if not api_key.strip() or not model.strip():
            raise ExternalAPIError("Grounded provider API key and model are required.")
        self._api_key = api_key.strip()
        self._model = model.strip()
        self._logger = logger or logging.getLogger(__name__)
        self._http_client_factory = http_client_factory
        self._sleep = sleep

    async def _post(self, url: str, payload: dict[str, Any], headers: dict[str, str]) -> Mapping[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, DEFAULT_RETRY_COUNT + 1):
            try:
                async with self._http_client_factory(timeout=SEARCH_TIMEOUT_SECONDS, headers=headers) as client:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    data = response.json()
                if not isinstance(data, Mapping):
                    raise ExternalAPIError("Grounded provider returned a non-object JSON response.")
                return data
            except ExternalAPIError:
                raise
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in {429, 500, 502, 503, 504}:
                    raise ExternalAPIError("Grounded provider request failed.") from exc
                last_error = exc
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
            if attempt < DEFAULT_RETRY_COUNT:
                await self._sleep(DEFAULT_RETRY_DELAY_SECONDS * attempt)
        self._logger.error("Grounded provider request failed after retries.", extra={"attempts": DEFAULT_RETRY_COUNT})
        raise ExternalAPIError("Grounded provider request failed after retries.") from last_error

    async def aclose(self) -> None:
        return None


class GeminiGroundedProvider(_GroundedHTTPProvider):
    """Gemini generateContent with the official Google Search grounding tool."""

    _ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    @property
    def capability(self) -> ProviderCapability:
        return ProviderCapability(
            provider="GEMINI_GROUNDED_API",
            model=self._model,
            classification=ProviderClassification.GROUNDED_WITH_STRUCTURED_CITATIONS,
            web_grounding_supported=True,
            citations_supported=True,
            source_urls_supported=True,
        )

    async def run_visibility_prompt(self, prompt: MonitoredPrompt) -> ProviderResponse:
        data = await self._post(
            self._ENDPOINT.format(model=self._model),
            {"contents": [{"role": "user", "parts": [{"text": prompt.text}]}], "tools": [{"google_search": {}}]},
            {"x-goog-api-key": self._api_key, "content-type": "application/json"},
        )
        candidates = data.get("candidates", ())
        candidate = candidates[0] if isinstance(candidates, list) and candidates else {}
        content = candidate.get("content", {}) if isinstance(candidate, Mapping) else {}
        parts = content.get("parts", ()) if isinstance(content, Mapping) else ()
        text = "".join(str(part.get("text", "")) for part in parts if isinstance(part, Mapping)).strip()
        metadata = candidate.get("groundingMetadata", {}) if isinstance(candidate, Mapping) else {}
        chunks = metadata.get("groundingChunks", ()) if isinstance(metadata, Mapping) else ()
        citations: list[Citation] = []
        seen: set[str] = set()
        for chunk in chunks if isinstance(chunks, list) else ():
            web = chunk.get("web", {}) if isinstance(chunk, Mapping) else {}
            url = str(web.get("uri", "")).strip() if isinstance(web, Mapping) else ""
            if url and url not in seen:
                seen.add(url)
                citations.append(Citation(url=url, title=str(web.get("title", "")).strip(), index=len(citations) + 1))
        if not text:
            raise ExternalAPIError("Gemini grounded response did not contain text content.")
        return ProviderResponse(provider=self.capability.provider, model=self._model, prompt=prompt.text, response_text=text, citations=tuple(citations), provider_response_id=str(data.get("responseId") or "") or None, classification=self.capability.classification)


class PerplexitySonarGroundedProvider(_GroundedHTTPProvider):
    """Dedicated Perplexity Sonar generated-response adapter."""

    _ENDPOINT = "https://api.perplexity.ai/chat/completions"

    @property
    def capability(self) -> ProviderCapability:
        return ProviderCapability(
            provider="PERPLEXITY_SONAR_API",
            model=self._model,
            classification=ProviderClassification.GROUNDED_WITH_STRUCTURED_CITATIONS,
            web_grounding_supported=True,
            citations_supported=True,
            source_urls_supported=True,
        )

    async def run_visibility_prompt(self, prompt: MonitoredPrompt) -> ProviderResponse:
        data = await self._post(
            self._ENDPOINT,
            {"model": self._model, "messages": [{"role": "user", "content": prompt.text}]},
            {"Authorization": f"Bearer {self._api_key}", "content-type": "application/json"},
        )
        choices = data.get("choices", ())
        choice = choices[0] if isinstance(choices, list) and choices else {}
        message = choice.get("message", {}) if isinstance(choice, Mapping) else {}
        text = str(message.get("content", "")).strip() if isinstance(message, Mapping) else ""
        search_results = data.get("search_results", ())
        titles = {str(item.get("url", "")): str(item.get("title", "")) for item in search_results if isinstance(item, Mapping)} if isinstance(search_results, list) else {}
        raw_citations = data.get("citations", ())
        citations = tuple(Citation(url=url, title=titles.get(url, ""), index=index) for index, raw in enumerate(raw_citations if isinstance(raw_citations, list) else (), 1) if (url := str(raw).strip()))
        if not text:
            raise ExternalAPIError("Perplexity Sonar response did not contain text content.")
        return ProviderResponse(provider=self.capability.provider, model=self._model, prompt=prompt.text, response_text=text, citations=citations, provider_response_id=str(data.get("id") or "") or None, classification=self.capability.classification)


class OpenAIGroundedProvider(_GroundedHTTPProvider):
    """Dedicated OpenAI Responses web-search adapter; ordinary generation is unchanged."""

    _ENDPOINT = "https://api.openai.com/v1/responses"

    @property
    def capability(self) -> ProviderCapability:
        return ProviderCapability(provider="OPENAI_GROUNDED_API", model=self._model, classification=ProviderClassification.GROUNDED_WITH_STRUCTURED_CITATIONS, web_grounding_supported=True, citations_supported=True, source_urls_supported=True)

    async def run_visibility_prompt(self, prompt: MonitoredPrompt) -> ProviderResponse:
        data = await self._post(self._ENDPOINT, {"model": self._model, "input": prompt.text, "tools": [{"type": "web_search"}]}, {"Authorization": f"Bearer {self._api_key}", "content-type": "application/json"})
        texts: list[str] = []; citations: list[Citation] = []; seen: set[str] = set()
        for item in data.get("output", ()) if isinstance(data.get("output"), list) else ():
            for block in item.get("content", ()) if isinstance(item, Mapping) and isinstance(item.get("content"), list) else ():
                if not isinstance(block, Mapping): continue
                if block.get("type") == "output_text": texts.append(str(block.get("text", "")))
                for annotation in block.get("annotations", ()) if isinstance(block.get("annotations"), list) else ():
                    if not isinstance(annotation, Mapping) or annotation.get("type") != "url_citation": continue
                    url = str(annotation.get("url", "")).strip()
                    if url and url not in seen:
                        seen.add(url); citations.append(Citation(url=url, title=str(annotation.get("title", "")).strip(), index=len(citations) + 1))
        text = "".join(texts).strip()
        if not text: raise ExternalAPIError("OpenAI grounded response did not contain text content.")
        return ProviderResponse(provider=self.capability.provider, model=self._model, prompt=prompt.text, response_text=text, citations=tuple(citations), provider_response_id=str(data.get("id") or "") or None, classification=self.capability.classification)


class ClaudeGroundedProvider(_GroundedHTTPProvider):
    """Dedicated Anthropic Messages web-search adapter."""

    _ENDPOINT = "https://api.anthropic.com/v1/messages"

    @property
    def capability(self) -> ProviderCapability:
        return ProviderCapability(provider="CLAUDE_GROUNDED_API", model=self._model, classification=ProviderClassification.GROUNDED_WITH_STRUCTURED_CITATIONS, web_grounding_supported=True, citations_supported=True, source_urls_supported=True)

    async def run_visibility_prompt(self, prompt: MonitoredPrompt) -> ProviderResponse:
        data = await self._post(self._ENDPOINT, {"model": self._model, "max_tokens": 2000, "messages": [{"role": "user", "content": prompt.text}], "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}]}, {"x-api-key": self._api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        texts: list[str] = []; citations: list[Citation] = []; seen: set[str] = set()
        for block in data.get("content", ()) if isinstance(data.get("content"), list) else ():
            if not isinstance(block, Mapping): continue
            if block.get("type") == "text": texts.append(str(block.get("text", "")))
            candidates = list(block.get("citations", ())) if isinstance(block.get("citations"), list) else []
            result = block.get("content", ()) if block.get("type") == "web_search_tool_result" else ()
            if isinstance(result, list): candidates.extend(result)
            for source in candidates:
                if not isinstance(source, Mapping): continue
                url = str(source.get("url", "")).strip()
                if url and url not in seen:
                    seen.add(url); citations.append(Citation(url=url, title=str(source.get("title", "")).strip(), index=len(citations) + 1))
        text = "".join(texts).strip()
        if not text: raise ExternalAPIError("Claude grounded response did not contain text content.")
        return ProviderResponse(provider=self.capability.provider, model=self._model, prompt=prompt.text, response_text=text, citations=tuple(citations), provider_response_id=str(data.get("id") or "") or None, classification=self.capability.classification)
