"""AI intelligence adapter for normalized research prospects."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
from collections.abc import Mapping
from typing import Any

from src.core.exceptions import AIAnalysisError
from src.core.interfaces import IAIAnalysisService


class AIAnalysisService(IAIAnalysisService):
    """Turn provider output into validated, provider-neutral prospect intelligence."""

    _SYSTEM_PROMPT = (
        "You are a B2B SEO prospect analyst. Return only a JSON object with "
        "ai_score, guest_post_probability, category, priority, summary, and reason. "
        "Scores must be numeric values from 0 through 100; priority must be low, "
        "medium, high, or critical."
    )

    def __init__(self, ai_provider: Any, logger: logging.Logger | None = None) -> None:
        self._ai_provider = ai_provider
        self._logger = logger or logging.getLogger(__name__)

    @property
    def service_name(self) -> str:
        """Return the service identifier."""
        return "AIAnalysisService"

    async def analyze(self, website_data: dict[str, Any]) -> dict[str, Any]:
        """Request analysis from the injected provider and normalize its response."""
        if not isinstance(website_data, dict):
            raise AIAnalysisError("Website data must be a dictionary.")

        prompt = self._build_prompt(website_data)
        try:
            result = await self._generate(prompt)
            return self._normalize(result)
        except AIAnalysisError:
            raise
        except Exception as exc:
            self._logger.exception("AI analysis failed.")
            raise AIAnalysisError("Unable to analyze website.") from exc

    async def _generate(self, prompt: str) -> Any:
        """Call either the current async generate contract or legacy chat helper."""
        generate = getattr(self._ai_provider, "generate", None)
        if callable(generate):
            if inspect.iscoroutinefunction(generate):
                return await generate(prompt)
            return await asyncio.to_thread(generate, prompt)

        chat = getattr(self._ai_provider, "chat", self._ai_provider)
        if not callable(chat):
            raise AIAnalysisError("AI provider exposes neither generate() nor chat().")
        if inspect.iscoroutinefunction(chat):
            return await chat(self._SYSTEM_PROMPT, prompt)
        return await asyncio.to_thread(chat, self._SYSTEM_PROMPT, prompt)

    @classmethod
    def _build_prompt(cls, website_data: Mapping[str, Any]) -> str:
        """Serialize only relevant prospect data into a deterministic user prompt."""
        payload = {
            key: website_data.get(key)
            for key in (
                "domain",
                "url",
                "title",
                "description",
                "category",
                "email",
                "contact_page",
                "about_page",
            )
        }
        return "Analyze this website prospect:\n" + json.dumps(
            payload,
            ensure_ascii=False,
            default=str,
        )

    @classmethod
    def _normalize(cls, result: Any) -> dict[str, Any]:
        """Validate provider output and normalize optional intelligence fields."""
        payload = cls._parse_payload(result)
        return {
            "ai_score": cls._score(payload.get("ai_score")),
            "guest_post_probability": cls._score(
                payload.get("guest_post_probability")
            ),
            "category": cls._text(payload.get("category"), 200),
            "priority": cls._priority(payload.get("priority")),
            "summary": cls._text(payload.get("summary"), 10_000),
            "reason": cls._text(payload.get("reason"), 10_000),
        }

    @staticmethod
    def _parse_payload(result: Any) -> Mapping[str, Any]:
        """Decode mapping or fenced/plain JSON response data."""
        if isinstance(result, Mapping):
            return result
        if not isinstance(result, str):
            raise AIAnalysisError("AI provider returned an unsupported response type.")
        text = result.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AIAnalysisError("AI provider did not return valid JSON.") from exc
        if not isinstance(payload, Mapping):
            raise AIAnalysisError("AI provider JSON response must be an object.")
        return payload

    @staticmethod
    def _score(value: Any) -> float | None:
        """Return a bounded numeric score or None for absent values."""
        if value is None or value == "":
            return None
        try:
            score = float(value)
        except (TypeError, ValueError) as exc:
            raise AIAnalysisError("AI provider returned a non-numeric score.") from exc
        return max(0.0, min(100.0, score))

    @staticmethod
    def _text(value: Any, maximum_length: int) -> str:
        """Normalize text fields to model-safe bounded strings."""
        return " ".join(str(value or "").split())[:maximum_length]

    @staticmethod
    def _priority(value: Any) -> str:
        """Normalize the controlled priority vocabulary."""
        normalized = " ".join(str(value or "medium").lower().split())
        return normalized if normalized in {"low", "medium", "high", "critical"} else "medium"
