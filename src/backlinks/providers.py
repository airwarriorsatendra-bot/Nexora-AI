"""Replaceable authority-metrics and backlink-evidence provider boundaries."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

import httpx

from src.backlinks.domain.backlink import Backlink
from src.backlinks.domain.intelligence import AuthorityObservation, AuthorityScope, AuthorityStatus
from src.core.constants import DEFAULT_RETRY_COUNT, DEFAULT_RETRY_DELAY_SECONDS, SEARCH_TIMEOUT_SECONDS
from src.core.exceptions import AuthorityProviderError, AuthorityValidationError


@runtime_checkable
class AuthorityMetricsProvider(Protocol):
    provider_name: str
    async def observe(self, query: str, scope: AuthorityScope) -> AuthorityObservation: ...
    async def aclose(self) -> None: ...


@runtime_checkable
class BacklinkProvider(Protocol):
    provider_name: str
    async def observations(self, target: str) -> Sequence[Backlink]: ...
    async def aclose(self) -> None: ...


class MozAuthorityProvider:
    """Moz JSON-RPC site metrics adapter using only ``x-moz-token``."""

    provider_name = "MOZ"
    endpoint = "https://api.moz.com/jsonrpc"
    retryable_statuses = {429, 500, 502, 503, 504}

    def __init__(self, api_token: str, *, client: httpx.AsyncClient | None = None, client_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient, sleep: Callable[[float], Awaitable[None]] = asyncio.sleep, logger: logging.Logger | None = None) -> None:
        if not api_token.strip():
            raise AuthorityProviderError("MOZ_API_TOKEN is required for Moz authority enrichment.")
        self._token = api_token.strip()
        self._client = client
        self._client_factory = client_factory
        self._sleep = sleep
        self._logger = logger or logging.getLogger(__name__)
        self._owns_client = client is None

    async def observe(self, query: str, scope: AuthorityScope) -> AuthorityObservation:
        if not isinstance(scope, AuthorityScope):
            try: scope = AuthorityScope(scope)
            except ValueError as exc: raise AuthorityValidationError("Moz authority scope must be domain, subdomain, subfolder, or url.") from exc
        payload = {"jsonrpc": "2.0", "id": str(uuid4()), "method": "data.site.metrics.fetch", "params": {"data": {"site_query": {"query": query, "scope": scope.value}}}}
        data = await self._request(payload)
        result = data.get("result")
        if not isinstance(result, dict) or not isinstance(result.get("site_metrics"), dict):
            raise AuthorityProviderError("Moz authority response did not contain site metrics.")
        metrics = result["site_metrics"]
        allowed = ("domain_authority", "page_authority", "spam_score", "link_propensity", "http_code", "root_domain", "subdomain", "last_crawled", "pages_to_page", "external_pages_to_page", "root_domains_to_page", "pages_to_root_domain", "external_pages_to_root_domain", "root_domains_to_root_domain")
        values = {name: metrics.get(name) for name in allowed}
        values["http_status"] = values.pop("http_code")
        metric_names = ("domain_authority", "page_authority", "spam_score", "link_propensity")
        status = AuthorityStatus.AVAILABLE if any(values[name] is not None for name in metric_names) else AuthorityStatus.NOT_AVAILABLE
        return AuthorityObservation(provider=self.provider_name, target=query, scope=scope, status=status, **values)

    async def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, DEFAULT_RETRY_COUNT + 1):
            try:
                client = await self._get_client()
                response = await client.post(self.endpoint, json=payload)
                if response.status_code not in self.retryable_statuses:
                    response.raise_for_status()
                elif response.status_code >= 400:
                    response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict):
                    raise AuthorityProviderError("Moz returned a non-object JSON response.")
                error = data.get("error")
                if isinstance(error, dict):
                    code = error.get("code")
                    raw_status = error.get("status")
                    status = int(raw_status) if isinstance(raw_status, (int, str)) and str(raw_status).isdigit() else 0
                    if code == -32652 or status in {400, 401, 403, 404}:
                        raise AuthorityValidationError("Moz rejected deterministic authority request parameters.")
                    raise AuthorityProviderError("Moz returned a JSON-RPC provider error.")
                return data
            except (AuthorityValidationError, AuthorityProviderError):
                raise
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in self.retryable_statuses:
                    raise AuthorityProviderError("Moz authority request failed.") from exc
                last_error = exc
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
            if attempt < DEFAULT_RETRY_COUNT:
                await self._sleep(DEFAULT_RETRY_DELAY_SECONDS * attempt)
        self._logger.error("Moz authority request failed after bounded retries.", extra={"attempts": DEFAULT_RETRY_COUNT})
        raise AuthorityProviderError("Moz authority request failed after bounded retries.") from last_error

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = self._client_factory(timeout=SEARCH_TIMEOUT_SECONDS, headers={"x-moz-token": self._token, "content-type": "application/json"})
        return self._client

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None


class OfflineAuthorityProvider:
    provider_name = "MOZ"
    def __init__(self, observations: dict[tuple[str, AuthorityScope], AuthorityObservation] | None = None) -> None:
        self.observations = observations or {}
        self.calls: list[tuple[str, AuthorityScope]] = []
    async def observe(self, query: str, scope: AuthorityScope) -> AuthorityObservation:
        self.calls.append((query, scope))
        value = self.observations.get((query, scope))
        if value is not None: return value
        return AuthorityObservation(target=query, scope=scope, domain_authority=40, page_authority=30, spam_score=2, link_propensity=0.1, http_status=200, root_domain=query, pages_to_page=10, external_pages_to_page=5, root_domains_to_page=4, pages_to_root_domain=100, external_pages_to_root_domain=50, root_domains_to_root_domain=20)
    async def aclose(self) -> None: return None
