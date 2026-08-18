"""Secure bounded BFS crawler reusing Nexora's existing SSRF validation."""
from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup

from src.core.constants import DEFAULT_USER_AGENT, MAX_HTML_SIZE_BYTES, MAX_REDIRECTS
from src.core.exceptions import CrawlError
from src.research.services.crawler_service import CrawlerService
from src.site_crawl.domain import RedirectEdge, SiteCrawlRequest


@dataclass(frozen=True, slots=True)
class FetchResult:
    requested_url: str
    final_url: str
    status_code: int | None
    content_type: str
    body: str
    headers: dict[str, str]
    redirects: tuple[RedirectEdge, ...] = ()
    error: str | None = None


@dataclass(frozen=True, slots=True)
class RawPage:
    result: FetchResult
    depth: int
    discovered_from: str | None


def normalize_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise CrawlError("Site crawler accepts only absolute HTTP(S) URLs.")
    scheme = parsed.scheme.lower()
    host = parsed.hostname.rstrip(".").lower()
    port = parsed.port
    netloc = host if port is None or (scheme == "http" and port == 80) or (scheme == "https" and port == 443) else f"{host}:{port}"
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/") or "/"
    query = urlencode(parse_qsl(parsed.query, keep_blank_values=True), doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


class SecurePageFetcher:
    """Status-aware fetcher retaining the existing crawler's destination checks."""
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._provided_client = client
        self._owned_client: httpx.AsyncClient | None = None

    async def _client(self, timeout: float) -> httpx.AsyncClient:
        if self._provided_client is not None:
            return self._provided_client
        if self._owned_client is None:
            self._owned_client = httpx.AsyncClient(timeout=timeout, follow_redirects=False, headers={"User-Agent": DEFAULT_USER_AGENT})
        return self._owned_client

    async def fetch(self, url: str, timeout: float) -> FetchResult:
        current = await CrawlerService._validate_destination(CrawlerService._validate_url(url))
        redirects: list[RedirectEdge] = []
        client = await self._client(timeout)
        try:
            for _ in range(MAX_REDIRECTS + 1):
                response = await client.get(current)
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        return FetchResult(url, current, response.status_code, "", "", dict(response.headers), tuple(redirects), "Redirect location missing")
                    target = normalize_url(urljoin(current, location))
                    target = await CrawlerService._validate_destination(CrawlerService._validate_url(target))
                    redirects.append(RedirectEdge(source_url=current, target_url=target, status_code=response.status_code))
                    current = target
                    continue
                body = response.content[: MAX_HTML_SIZE_BYTES + 1]
                if len(body) > MAX_HTML_SIZE_BYTES:
                    return FetchResult(url, current, response.status_code, response.headers.get("content-type", ""), "", dict(response.headers), tuple(redirects), "Response exceeded size limit")
                return FetchResult(url, current, response.status_code, response.headers.get("content-type", ""), body.decode(response.encoding or "utf-8", errors="replace"), dict(response.headers), tuple(redirects))
            return FetchResult(url, current, None, "", "", {}, tuple(redirects), "Redirect limit exceeded")
        except (httpx.TimeoutException, httpx.TransportError):
            return FetchResult(url, current, None, "", "", {}, tuple(redirects), "Request timed out or was unreachable")

    async def aclose(self) -> None:
        if self._owned_client is not None:
            await self._owned_client.aclose()


class BoundedSiteCrawler:
    def __init__(self, fetch: Callable[[str, float], Awaitable[FetchResult]], close: Callable[[], Awaitable[None]] | None = None, destination_validator=None) -> None:
        self._fetch = fetch
        self._close = close
        self._destination_validator = destination_validator or self._validate_live_destination

    @staticmethod
    async def _validate_live_destination(url: str) -> str:
        return await CrawlerService._validate_destination(CrawlerService._validate_url(url))

    @staticmethod
    def _allowed(candidate: str, origin: str, request: SiteCrawlRequest) -> bool:
        try:
            parsed, root = urlsplit(candidate), urlsplit(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                return False
            host, root_host = parsed.hostname.lower(), root.hostname.lower()
            if request.same_host_only:
                return host == root_host or (request.include_subdomains and host.endswith("." + root_host))
            return True
        except (ValueError, AttributeError):
            return False

    async def crawl(self, request: SiteCrawlRequest) -> tuple[RawPage, ...]:
        start = normalize_url(str(request.start_url))
        await self._destination_validator(start)
        frontier = deque([(start, 0, None)])
        queued, visited, pages = {start}, set(), []
        while frontier and len(pages) < request.max_pages:
            batch = []
            while frontier and len(batch) < request.max_concurrency and len(pages) + len(batch) < request.max_pages:
                item = frontier.popleft()
                if item[0] not in visited:
                    visited.add(item[0]); batch.append(item)
            results = await asyncio.gather(*(self._fetch(url, request.timeout_seconds) for url, _, _ in batch))
            for (url, depth, source), result in zip(batch, results, strict=True):
                pages.append(RawPage(result, depth, source))
                if depth >= request.max_depth or not result.body or "html" not in result.content_type.lower():
                    continue
                soup = BeautifulSoup(result.body, "lxml")
                for anchor in soup.find_all("a", href=True):
                    href = str(anchor.get("href", "")).strip()
                    if not href or href.lower().startswith(("mailto:", "tel:", "javascript:", "data:", "file:", "ftp:")):
                        continue
                    try:
                        candidate = normalize_url(urljoin(result.final_url, href))
                    except (CrawlError, ValueError):
                        continue
                    if self._allowed(candidate, start, request) and candidate not in queued:
                        queued.add(candidate); frontier.append((candidate, depth + 1, result.final_url))
            if request.request_delay_seconds and frontier:
                await asyncio.sleep(request.request_delay_seconds)
        return tuple(pages)

    async def aclose(self) -> None:
        if self._close is not None:
            await self._close()
