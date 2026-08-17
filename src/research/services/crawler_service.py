"""HTTP crawler and metadata extractor for research prospects."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import re
import socket
from collections.abc import Callable
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from src.core.constants import (
    CRAWL_TIMEOUT_SECONDS,
    DEFAULT_RETRY_COUNT,
    DEFAULT_RETRY_DELAY_SECONDS,
    DEFAULT_USER_AGENT,
    MAX_HTML_SIZE_BYTES,
    MAX_REDIRECTS,
)
from src.core.exceptions import CrawlError
from src.core.interfaces import ICrawlerService


class CrawlerService(ICrawlerService):
    """Fetch an HTML page asynchronously and extract prospect contact data."""

    _EMAIL_PATTERN = re.compile(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    )
    _PHONE_PATTERN = re.compile(r"\+?\d[\d\s().-]{7,}\d")
    _SOCIAL_DOMAINS = {
        "facebook": "facebook.com",
        "instagram": "instagram.com",
        "linkedin": "linkedin.com",
        "twitter": "twitter.com",
        "youtube": "youtube.com",
    }

    def __init__(
        self,
        logger: logging.Logger | None = None,
        http_client_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient,
    ) -> None:
        self._logger = logger or logging.getLogger(__name__)
        self._http_client_factory = http_client_factory

    @property
    def service_name(self) -> str:
        """Return the crawler service identifier."""
        return "CrawlerService"

    async def crawl(self, url: str) -> dict[str, Any]:
        """Download one valid HTTP(S) URL and return normalized extracted data."""
        normalized_url = await self._validate_destination(self._validate_url(url))
        html = await self.fetch_html(normalized_url)
        return self._extract(html, normalized_url)

    async def fetch_html(self, url: str) -> str:
        """Fetch bounded HTML for consumers that perform their own interpretation."""
        return await self._download(await self._validate_destination(self._validate_url(url)))

    @staticmethod
    def _validate_url(url: str) -> str:
        """Validate the URL before an outbound request is made."""
        normalized = url.strip()
        parsed = urlparse(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise CrawlError("Crawler accepts only absolute HTTP(S) URLs.")
        hostname = parsed.hostname.rstrip(".").lower()
        if hostname == "localhost" or hostname.endswith(".localhost"):
            raise CrawlError("Crawler does not permit local destinations.")
        try:
            address = ipaddress.ip_address(hostname)
        except ValueError:
            return normalized
        if not address.is_global:
            raise CrawlError("Crawler does not permit private or reserved destinations.")
        return normalized

    @staticmethod
    async def _validate_destination(url: str) -> str:
        """Reject hostnames resolving to non-public addresses before connecting."""
        parsed = urlparse(url)
        hostname = parsed.hostname
        if hostname is None:
            raise CrawlError("Crawler accepts only absolute HTTP(S) URLs.")
        try:
            ipaddress.ip_address(hostname)
            return url
        except ValueError:
            pass
        try:
            addresses = await asyncio.get_running_loop().getaddrinfo(
                hostname, parsed.port or (443 if parsed.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        except socket.gaierror as exc:
            raise CrawlError("Crawler could not resolve the destination host.") from exc
        resolved = {record[4][0] for record in addresses}
        if not resolved or any(not ipaddress.ip_address(address).is_global for address in resolved):
            raise CrawlError("Crawler does not permit destinations resolving to private or reserved addresses.")
        return url

    async def _download(self, url: str) -> str:
        """Download a bounded HTML response with transient-failure retries."""
        last_error: Exception | None = None
        for attempt in range(1, DEFAULT_RETRY_COUNT + 1):
            try:
                current_url = url
                for _ in range(MAX_REDIRECTS + 1):
                    async with self._http_client_factory(
                        timeout=CRAWL_TIMEOUT_SECONDS,
                        follow_redirects=False,
                        max_redirects=MAX_REDIRECTS,
                        headers={"User-Agent": DEFAULT_USER_AGENT},
                    ) as client, client.stream("GET", current_url) as response:
                        if response.is_redirect:
                            location = response.headers.get("location")
                            if not location:
                                raise CrawlError("Redirect response is missing a location.")
                            current_url = await self._validate_destination(self._validate_url(urljoin(current_url, location)))
                            continue
                        response.raise_for_status()
                        content_type = response.headers.get("content-type", "")
                        if "html" not in content_type.lower():
                            raise CrawlError("The response is not an HTML document.")
                        chunks: list[bytes] = []
                        size = 0
                        async for chunk in response.aiter_bytes():
                            size += len(chunk)
                            if size > MAX_HTML_SIZE_BYTES:
                                raise CrawlError("The HTML response exceeds the size limit.")
                            chunks.append(chunk)
                        return b"".join(chunks).decode(
                            response.encoding or "utf-8",
                            errors="replace",
                        )
                raise CrawlError("Crawler exceeded the redirect limit.")
            except CrawlError:
                raise
            except (httpx.HTTPStatusError, httpx.TransportError, httpx.TimeoutException) as exc:
                last_error = exc
                if attempt < DEFAULT_RETRY_COUNT:
                    await asyncio.sleep(DEFAULT_RETRY_DELAY_SECONDS * attempt)
                continue
            except Exception as exc:
                raise CrawlError(f"Unable to crawl '{url}'.") from exc

        raise CrawlError(f"Unable to crawl '{url}' after {DEFAULT_RETRY_COUNT} attempts.") from last_error

    def _extract(self, html: str, base_url: str) -> dict[str, Any]:
        """Extract the first usable contact and social values from HTML."""
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text(" ", strip=True)
        links = [
            urljoin(base_url, href.strip())
            for anchor in soup.find_all("a", href=True)
            if (href := anchor.get("href")) and href.strip()
        ]
        return {
            "email": self._first_email(text, links),
            "phone": self._first_phone(text),
            "facebook": self._social_link(links, "facebook"),
            "instagram": self._social_link(links, "instagram"),
            "linkedin": self._social_link(links, "linkedin"),
            "twitter": self._social_link(links, "twitter"),
            "youtube": self._social_link(links, "youtube"),
            "about_page": self._keyword_link(links, "about"),
            "contact_page": self._keyword_link(links, "contact"),
        }

    def _first_email(self, text: str, links: list[str]) -> str | None:
        """Return the first email from a mailto link or visible page text."""
        for link in links:
            if link.lower().startswith("mailto:"):
                value = link[7:].split("?", 1)[0]
                if self._EMAIL_PATTERN.fullmatch(value):
                    return value
        match = self._EMAIL_PATTERN.search(text)
        return match.group(0) if match else None

    def _first_phone(self, text: str) -> str | None:
        """Return the first normalized candidate phone number."""
        match = self._PHONE_PATTERN.search(text)
        return " ".join(match.group(0).split()) if match else None

    def _social_link(self, links: list[str], platform: str) -> str | None:
        """Find the first HTTP(S) social profile link for a platform."""
        domain = self._SOCIAL_DOMAINS[platform]
        for link in links:
            parsed = urlparse(link)
            hostname = (parsed.hostname or "").lower()
            if parsed.scheme in {"http", "https"} and (
                hostname == domain or hostname.endswith(f".{domain}")
            ):
                return link
        return None

    @staticmethod
    def _keyword_link(links: list[str], keyword: str) -> str | None:
        """Find a same-site candidate page based on a URL keyword."""
        for link in links:
            parsed = urlparse(link)
            if parsed.scheme in {"http", "https"} and keyword in parsed.path.lower():
                return link
        return None
