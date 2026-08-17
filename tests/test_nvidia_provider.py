"""Offline contract tests for the NVIDIA NIM research provider."""

from __future__ import annotations

import unittest
from collections import deque
from typing import Any

import httpx

from src.core.constants import DEFAULT_NVIDIA_BASE_URL
from src.core.enums import SearchProvider
from src.core.exceptions import ExternalAPIError
from src.research.composition import ResearchComposition, ResearchSettings
from src.research.providers.claude_provider import ClaudeProvider
from src.research.providers.gemini_provider import GeminiProvider
from src.research.providers.groq_provider import GroqProvider
from src.research.providers.nvidia_provider import NvidiaProvider
from src.research.providers.openai_provider import OpenAIProvider


class _Response:
    def __init__(self, payload: Any = None, error: Exception | None = None) -> None:
        self.payload = payload
        self.error = error

    def raise_for_status(self) -> None:
        if self.error:
            raise self.error

    def json(self) -> Any:
        return self.payload


class _Client:
    def __init__(self, outcomes: deque[Any], calls: list[tuple[str, dict[str, Any]]]) -> None:
        self._outcomes = outcomes
        self._calls = calls

    async def __aenter__(self) -> "_Client":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        return None

    async def post(self, url: str, *, json: dict[str, Any]) -> _Response:
        self._calls.append((url, json))
        outcome = self._outcomes.popleft()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class _ClientFactory:
    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = deque(outcomes)
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.options: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> _Client:
        self.options.append(kwargs)
        return _Client(self.outcomes, self.calls)


class NvidiaProviderTests(unittest.IsolatedAsyncioTestCase):
    def _provider(self, factory: _ClientFactory, sleeps: list[float] | None = None) -> NvidiaProvider:
        async def sleep(delay: float) -> None:
            if sleeps is not None:
                sleeps.append(delay)

        return NvidiaProvider(
            "nvidia-key",
            "meta/llama-3.3-70b-instruct",
            http_client_factory=factory,
            sleep=sleep,
        )

    def test_constructor_validates_required_configuration(self) -> None:
        with self.assertRaises(ExternalAPIError):
            NvidiaProvider("", "model")
        with self.assertRaises(ExternalAPIError):
            NvidiaProvider("key", "")
        with self.assertRaises(ExternalAPIError):
            NvidiaProvider("key", "model", base_url="")

    async def test_successfully_normalizes_openai_compatible_content(self) -> None:
        factory = _ClientFactory([_Response({"choices": [{"message": {"content": '{"ai_score": 91}'}}]})])
        result = await self._provider(factory).generate("analyze prospect")

        self.assertEqual(result, '{"ai_score": 91}')
        self.assertEqual(factory.calls[0][0], f"{DEFAULT_NVIDIA_BASE_URL}/chat/completions")
        self.assertEqual(factory.calls[0][1]["model"], "meta/llama-3.3-70b-instruct")
        self.assertEqual(factory.options[0]["headers"]["Authorization"], "Bearer nvidia-key")

    async def test_rejects_malformed_response(self) -> None:
        factory = _ClientFactory([_Response({"choices": [{"message": {"content": ""}}]})])
        with self.assertRaises(ExternalAPIError):
            await self._provider(factory).generate("analyze prospect")

    async def test_timeout_retries_then_succeeds(self) -> None:
        sleeps: list[float] = []
        factory = _ClientFactory([
            httpx.TimeoutException("timed out"),
            _Response({"choices": [{"message": {"content": "{}"}}]}),
        ])
        result = await self._provider(factory, sleeps).generate("analyze prospect")

        self.assertEqual(result, "{}")
        self.assertEqual(len(factory.calls), 2)
        self.assertEqual(sleeps, [2])

    async def test_transport_and_http_failures_are_chained_after_retries(self) -> None:
        request = httpx.Request("POST", "https://example.test")
        response = httpx.Response(500, request=request)
        factory = _ClientFactory([
            httpx.TransportError("offline"),
            _Response(error=httpx.HTTPStatusError("server error", request=request, response=response)),
            httpx.TransportError("offline"),
        ])
        sleeps: list[float] = []

        with self.assertRaises(ExternalAPIError) as raised:
            await self._provider(factory, sleeps).generate("analyze prospect")

        self.assertIsInstance(raised.exception.__cause__, httpx.TransportError)
        self.assertEqual(len(factory.calls), 3)
        self.assertEqual(sleeps, [2, 4])

    async def test_composition_supports_nvidia_and_existing_ai_providers(self) -> None:
        environment = {
            "SEARCH_PROVIDER": "tavily",
            "TAVILY_API_KEY": "search-key",
            "AI_PROVIDER": "nvidia",
            "NVIDIA_API_KEY": "nvidia-key",
        }
        settings = ResearchSettings.from_environment(environment)
        self.assertEqual(settings.ai_provider, "nvidia")
        application = ResearchComposition(settings).build()
        self.assertIsInstance(application.ai_analysis_service._ai_provider, NvidiaProvider)
        await application.aclose()

        providers = {
            "openai": OpenAIProvider("key", "model"),
            "gemini": GeminiProvider("key", "model"),
            "groq": GroqProvider("key", "model"),
            "claude": ClaudeProvider("key", "model"),
        }
        self.assertEqual(set(providers), {"openai", "gemini", "groq", "claude"})
        self.assertEqual(settings.search_provider, SearchProvider.TAVILY)
