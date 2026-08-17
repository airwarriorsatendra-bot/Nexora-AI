"""Pure URL and domain normalization used by the backlinks vertical."""

from __future__ import annotations

from urllib.parse import urlparse, urlunparse

from src.core.exceptions import BacklinkError


def canonical_url(value: str) -> str:
    """Return a stable absolute HTTP(S) URL without a fragment."""
    parsed = urlparse(value.strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise BacklinkError("Backlink URLs must be absolute HTTP(S) URLs.")
    host = parsed.hostname.lower()
    if parsed.port:
        host = f"{host}:{parsed.port}"
    path = parsed.path or "/"
    return urlunparse((parsed.scheme.lower(), host, path, "", parsed.query, ""))


def normalized_domain(value: str) -> str:
    """Return a normalized hostname from an HTTP(S) URL or hostname."""
    candidate = value.strip().lower()
    parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
    if not parsed.hostname:
        raise BacklinkError("A valid domain is required.")
    return parsed.hostname.lower().removeprefix("www.")
