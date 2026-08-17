"""Deterministic technical and on-page SEO interpretation service."""

from __future__ import annotations

import logging
import json
import re
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from src.core.enums import Priority
from src.core.exceptions import CrawlError, RepositoryError, ServiceError
from src.seo.domain.seo_audit import SEOAudit
from src.seo.domain.seo_issue import SEOIssue
from src.seo.dto.seo_audit_request import SEOAuditRequest
from src.seo.dto.seo_audit_response import SEOAuditResponse
from src.seo.repositories.seo_audit_repository import SEOAuditRepository


class SEOAuditService:
    """Audit parsed HTML deterministically; AI and paid metrics are deliberately optional."""

    _CATEGORY_WEIGHTS = ("technical", "on_page", "content", "structured_data", "images", "links")
    _DEDUCTIONS = {Priority.CRITICAL: 30.0, Priority.HIGH: 15.0, Priority.MEDIUM: 8.0, Priority.LOW: 3.0}

    def __init__(
        self,
        fetch_html: Callable[[str], Awaitable[str]],
        repository: SEOAuditRepository,
        logger: logging.Logger | None = None,
    ) -> None:
        self._fetch_html = fetch_html
        self._repository = repository
        self._logger = logger or logging.getLogger(__name__)

    async def audit(self, request: SEOAuditRequest) -> SEOAuditResponse:
        """Fetch, inspect, score, and persist one audit without hiding failures."""
        url = str(request.url)
        try:
            html = await self._fetch_html(url)
            audit = self.analyze_html(url, html)
            await self._repository.save(audit)
            return SEOAuditResponse(success=True, audit=audit, message="SEO audit completed.")
        except CrawlError as exc:
            self._logger.warning("SEO crawl failed.", extra={"url": url})
            return SEOAuditResponse(success=False, errors=[str(exc)], message="SEO audit could not fetch the page.")
        except RepositoryError as exc:
            self._logger.exception("SEO audit persistence failed.", extra={"url": url})
            return SEOAuditResponse(success=False, errors=[str(exc)], message="SEO audit could not be saved.")
        except Exception as exc:
            self._logger.exception("SEO audit failed.", extra={"url": url})
            raise ServiceError("SEO audit failed unexpectedly.") from exc

    def analyze_html(self, url: str, html: str) -> SEOAudit:
        """Produce reproducible findings from a bounded HTML document."""
        soup = BeautifulSoup(html or "", "lxml")
        issues: list[SEOIssue] = []
        add = lambda code, category, severity, title, description, evidence, recommendation: issues.append(
            SEOIssue(code=code, category=category, severity=severity, title=title, description=description, evidence=evidence, recommendation=recommendation, affected_url=url)
        )
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        description_tag = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
        description = str(description_tag.get("content", "")).strip() if description_tag else ""
        canonical_tags = soup.find_all("link", attrs={"rel": lambda value: value and "canonical" in value})
        robots_tag = soup.find("meta", attrs={"name": re.compile("^robots$", re.I)})
        robots = str(robots_tag.get("content", "")).lower() if robots_tag else ""
        headings = soup.find_all(["h1", "h2", "h3"])
        h1s = soup.find_all("h1")
        text = soup.get_text(" ", strip=True)
        word_count = len(re.findall(r"\b\w+\b", text))

        if not title:
            add("missing_title", "on_page", Priority.HIGH, "Missing title", "The page has no title element.", "title is absent", "Add a unique, descriptive title.")
        elif len(title) < 20 or len(title) > 60:
            add("title_length", "on_page", Priority.LOW, "Title length is outside the recommended range", "Title length should normally be concise and descriptive.", f"{len(title)} characters", "Keep the title near 20–60 characters where practical.")
        if not description:
            add("missing_meta_description", "on_page", Priority.MEDIUM, "Missing meta description", "The page has no meta description.", "description is absent", "Add a concise page-specific meta description.")
        elif len(description) < 70 or len(description) > 160:
            add("meta_description_length", "on_page", Priority.LOW, "Meta description length is outside the recommended range", "Description length may reduce snippet usefulness.", f"{len(description)} characters", "Keep the description near 70–160 characters where practical.")
        if not h1s:
            add("missing_h1", "on_page", Priority.MEDIUM, "Missing H1", "The page has no H1 heading.", "0 H1 elements", "Add one descriptive H1.")
        elif len(h1s) > 1:
            add("multiple_h1", "on_page", Priority.MEDIUM, "Multiple H1 headings", "The page has more than one H1 heading.", f"{len(h1s)} H1 elements", "Use one primary H1 unless a documented template requires otherwise.")
        if not canonical_tags:
            add("missing_canonical", "technical", Priority.MEDIUM, "Missing canonical URL", "The page does not declare a canonical URL.", "canonical link is absent", "Add an absolute canonical URL.")
        elif len(canonical_tags) > 1:
            add("duplicate_canonical", "technical", Priority.HIGH, "Multiple canonical URLs", "Multiple canonical declarations create conflicting signals.", f"{len(canonical_tags)} canonical links", "Retain one canonical URL.")
        if "noindex" in robots:
            add("noindex", "technical", Priority.HIGH, "Page is marked noindex", "Robots directives request that search engines do not index this page.", robots, "Remove noindex only when the page should be indexed.")
        if word_count == 0:
            add("empty_page", "content", Priority.HIGH, "Page has no readable content", "No visible textual content was found.", "0 words", "Add useful, indexable page content.")
        elif word_count < 300:
            add("thin_content", "content", Priority.MEDIUM, "Thin content", "The page has limited visible content.", f"{word_count} words", "Expand content where it does not satisfy search intent.")
        if not headings and word_count:
            add("missing_heading_structure", "content", Priority.LOW, "Missing heading structure", "Readable content has no H1–H3 headings.", "0 headings", "Use headings to communicate content hierarchy.")

        images = soup.find_all("img")
        missing_alt = [image for image in images if not image.has_attr("alt") or not str(image.get("alt", "")).strip()]
        if missing_alt:
            add("missing_image_alt", "images", Priority.LOW, "Images lack alternative text", "Some images have missing or empty alt text.", f"{len(missing_alt)} of {len(images)} images", "Add meaningful alt text for informative images.")

        page_host = (urlparse(url).hostname or "").lower()
        internal_links = external_links = broken_internal = 0
        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href", "")).strip()
            if not href:
                continue
            resolved = urljoin(url, href)
            parsed = urlparse(resolved)
            if href == "#" or (parsed.scheme in {"http", "https"} and not parsed.hostname):
                broken_internal += 1
            elif parsed.hostname and parsed.hostname.lower() == page_host:
                internal_links += 1
            elif parsed.scheme in {"http", "https"}:
                external_links += 1
        if broken_internal:
            add("invalid_internal_link", "links", Priority.MEDIUM, "Invalid internal links", "Some internal links cannot resolve to a page URL.", f"{broken_internal} invalid links", "Replace placeholder or malformed internal links with valid URLs.")

        schema_types: set[str] = set()
        malformed_schema = 0
        for script in soup.find_all("script", attrs={"type": re.compile("application/ld\\+json", re.I)}):
            try:
                payload = json.loads(script.string or script.get_text())
                values = payload if isinstance(payload, list) else [payload]
                for value in values:
                    if isinstance(value, dict) and value.get("@type"):
                        schema_types.add(str(value["@type"]))
            except (TypeError, ValueError):
                malformed_schema += 1
        if malformed_schema:
            add("malformed_json_ld", "structured_data", Priority.MEDIUM, "Malformed JSON-LD", "Structured data could not be parsed as JSON.", f"{malformed_schema} invalid blocks", "Fix JSON-LD syntax before publishing.")

        metrics: dict[str, int | str | bool | None] = {
            "title": title, "title_length": len(title), "meta_description": description,
            "meta_description_length": len(description), "h1_count": len(h1s), "heading_count": len(headings),
            "word_count": word_count, "image_count": len(images), "missing_alt_count": len(missing_alt),
            "internal_links": internal_links, "external_links": external_links, "schema_types": ", ".join(sorted(schema_types)),
            "has_open_graph_title": bool(soup.find("meta", property="og:title")),
            "has_twitter_card": bool(soup.find("meta", attrs={"name": "twitter:card"})),
            "language": (soup.html or {}).get("lang") if soup.html else None,
        }
        scores = self._scores(issues)
        return SEOAudit(url=url, overall_score=round(sum(scores.values()) / len(scores), 2), category_scores=scores, issues=issues, metrics=metrics)

    def _scores(self, issues: list[SEOIssue]) -> dict[str, float]:
        scores = {category: 100.0 for category in self._CATEGORY_WEIGHTS}
        for issue in issues:
            scores[issue.category] = max(0.0, scores.get(issue.category, 100.0) - self._DEDUCTIONS[issue.severity])
        return scores
