"""OAuth refresh-token HTTP provider for the read-only Search Console API."""

from __future__ import annotations

import asyncio
import logging
from decimal import Decimal
from typing import Any
from urllib.parse import quote

import httpx

from src.core.constants import DEFAULT_RETRY_COUNT, GSC_API_BASE_URL, GSC_TIMEOUT_SECONDS, GSC_TOKEN_URL
from src.core.exceptions import AuthenticationError, AuthorizationError, ExternalAPIError
from src.search_console.domain import SearchConsoleProperty, SearchDimension, SearchPerformanceRecord
from src.search_console.dto import SearchAnalyticsRequest

logger = logging.getLogger(__name__)


class GoogleSearchConsoleProvider:
    """Uses only the minimum ``webmasters.readonly`` OAuth grant already issued to the beta operator."""

    provider_name = "GOOGLE_SEARCH_CONSOLE_API"

    def __init__(self, *, client_id: str, client_secret: str, refresh_token: str, http_client: httpx.AsyncClient | None = None, api_base_url: str = GSC_API_BASE_URL, token_url: str = GSC_TOKEN_URL, timeout_seconds: float = GSC_TIMEOUT_SECONDS, max_retries: int = DEFAULT_RETRY_COUNT) -> None:
        if not client_id.strip() or not client_secret.strip() or not refresh_token.strip():
            raise AuthenticationError("Google Search Console OAuth configuration is incomplete.")
        self._client_id, self._client_secret, self._refresh_token = client_id, client_secret, refresh_token
        self._client, self._owns_client = http_client, http_client is None
        self._api_base_url, self._token_url = api_base_url.rstrip("/"), token_url
        self._timeout, self._max_retries = timeout_seconds, max(0, max_retries)

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(self._timeout))
        return self._client

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
        self._client = None

    async def list_properties(self) -> tuple[SearchConsoleProperty, ...]:
        body = await self._request("GET", "/sites")
        entries = body.get("siteEntry", [])
        if not isinstance(entries, list):
            raise ExternalAPIError("Google Search Console returned an invalid properties response.")
        try:
            return tuple(SearchConsoleProperty(site_url=str(entry["siteUrl"]), permission_level=str(entry.get("permissionLevel", "unknown"))) for entry in entries if isinstance(entry, dict) and entry.get("siteUrl"))
        except (TypeError, ValueError) as exc:
            raise ExternalAPIError("Google Search Console returned an invalid property.") from exc

    async def query_search_analytics(self, request: SearchAnalyticsRequest) -> tuple[SearchPerformanceRecord, ...]:
        body = await self._request("POST", f"/sites/{quote(request.property.site_url, safe='')}/searchAnalytics/query", json={"startDate": request.period.start_date.isoformat(), "endDate": request.period.end_date.isoformat(), "dimensions": [item.value for item in request.dimensions], "rowLimit": request.row_limit, "type": "web"})
        rows = body.get("rows", [])
        if not isinstance(rows, list):
            raise ExternalAPIError("Google Search Console returned an invalid analytics response.")
        normalized: list[SearchPerformanceRecord] = []
        for row in rows:
            if not isinstance(row, dict):
                raise ExternalAPIError("Google Search Console returned a malformed analytics row.")
            keys = row.get("keys", [])
            if not isinstance(keys, list) or len(keys) != len(request.dimensions):
                raise ExternalAPIError("Google Search Console returned analytics keys that do not match dimensions.")
            try:
                normalized.append(SearchPerformanceRecord(dimensions=request.dimensions, keys=tuple(str(key) for key in keys), clicks=int(row.get("clicks", 0)), impressions=int(row.get("impressions", 0)), ctr=Decimal(str(row.get("ctr", 0))), average_position=Decimal(str(row.get("position", 0)))))
            except (ArithmeticError, TypeError, ValueError) as exc:
                raise ExternalAPIError("Google Search Console returned invalid analytics metrics.") from exc
        return tuple(normalized)

    async def _access_token(self) -> str:
        client = await self._http()
        try:
            response = await client.post(self._token_url, data={"client_id": self._client_id, "client_secret": self._client_secret, "refresh_token": self._refresh_token, "grant_type": "refresh_token"})
        except httpx.HTTPError as exc:
            raise ExternalAPIError("Google OAuth token request failed.") from exc
        if response.status_code in (400, 401):
            raise AuthenticationError("Google OAuth credentials were rejected.")
        if response.status_code >= 400:
            raise ExternalAPIError("Google OAuth token request failed.")
        try:
            token = response.json().get("access_token")
        except ValueError as exc:
            raise AuthenticationError("Google OAuth returned an invalid token response.") from exc
        if not isinstance(token, str) or not token:
            raise AuthenticationError("Google OAuth did not return an access token.")
        return token

    async def _request(self, method: str, path: str, *, json: dict[str, Any] | None = None) -> dict[str, Any]:
        token = await self._access_token()
        client = await self._http()
        for attempt in range(self._max_retries + 1):
            try:
                response = await client.request(method, f"{self._api_base_url}{path}", headers={"Authorization": f"Bearer {token}"}, json=json)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt < self._max_retries:
                    await asyncio.sleep(0.1 * (2 ** attempt))
                    continue
                raise ExternalAPIError("Google Search Console request timed out or could not connect.") from exc
            if response.status_code in (429, 500, 502, 503, 504) and attempt < self._max_retries:
                await asyncio.sleep(0.1 * (2 ** attempt))
                continue
            if response.status_code == 401:
                raise AuthenticationError("Google Search Console authentication failed.")
            if response.status_code == 403:
                raise AuthorizationError("Google account is not authorized for this Search Console property.")
            if response.status_code >= 400:
                raise ExternalAPIError(f"Google Search Console request failed with HTTP {response.status_code}.")
            try:
                data = response.json()
            except ValueError as exc:
                raise ExternalAPIError("Google Search Console returned invalid JSON.") from exc
            if not isinstance(data, dict):
                raise ExternalAPIError("Google Search Console returned an invalid response.")
            return data
        raise ExternalAPIError("Google Search Console request retry limit was exhausted.")
