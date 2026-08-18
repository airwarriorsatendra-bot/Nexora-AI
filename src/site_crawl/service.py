"""Deterministic site-wide technical and internal-link intelligence."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from src.site_crawl.crawler import BoundedSiteCrawler, RawPage, normalize_url
from src.site_crawl.domain import (
    CrawlComparison, CrawlIssue, CrawlStatistics, CrawledPage, IndexabilitySignal,
    InternalLink, LinkOpportunity, SiteCrawl, SiteCrawlRequest, TechnicalSiteSummary,
)
from src.site_crawl.repository import SiteCrawlRepository


class SiteCrawlService:
    """Coordinates bounded crawling, analysis, evidence bridging, and persistence."""
    def __init__(self, crawler: BoundedSiteCrawler, repository: SiteCrawlRepository, evidence_loader=None) -> None:
        self._crawler, self._repository, self._evidence_loader = crawler, repository, evidence_loader

    @staticmethod
    def _same_site(url: str, start: str, include_subdomains: bool) -> bool:
        host, root = (urlsplit(url).hostname or "").lower(), (urlsplit(start).hostname or "").lower()
        return host == root or (include_subdomains and host.endswith("." + root))

    @staticmethod
    def _schema_types(soup: BeautifulSoup) -> tuple[str, ...]:
        found = set()
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            try:
                value = json.loads(script.get_text(strip=True) or "null")
                values = value if isinstance(value, list) else [value]
                for item in values:
                    if isinstance(item, dict) and item.get("@type"):
                        types = item["@type"] if isinstance(item["@type"], list) else [item["@type"]]
                        found.update(str(kind) for kind in types)
            except (TypeError, ValueError):
                continue
        return tuple(sorted(found))

    def _analyze_raw(self, raw: RawPage, request: SiteCrawlRequest) -> tuple[CrawledPage, list[InternalLink], list[CrawlIssue]]:
        result, issues, links = raw.result, [], []
        normalized = normalize_url(result.final_url)
        status = result.status_code
        soup = BeautifulSoup(result.body, "lxml") if result.body and "html" in result.content_type.lower() else BeautifulSoup("", "lxml")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        description_tag = soup.find("meta", attrs={"name": lambda value: value and value.lower() == "description"})
        description = str(description_tag.get("content", "")).strip() if description_tag else ""
        h1s = tuple(node.get_text(" ", strip=True) for node in soup.find_all("h1"))
        canonical_tags = soup.find_all("link", rel=lambda value: value and "canonical" in [str(x).lower() for x in (value if isinstance(value, list) else [value])])
        canonical = normalize_url(urljoin(result.final_url, canonical_tags[0].get("href"))) if canonical_tags and canonical_tags[0].get("href") else None
        meta_robots = soup.find("meta", attrs={"name": lambda value: value and value.lower() == "robots"})
        robots = ",".join(filter(None, [str(meta_robots.get("content", "")) if meta_robots else "", result.headers.get("x-robots-tag", "")])).lower()
        text = soup.get_text(" ", strip=True); words = len(text.split())
        images = soup.find_all("img"); missing_alt = sum(not str(image.get("alt", "")).strip() for image in images)
        external = 0
        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href", "")).strip()
            if not href or href.lower().startswith(("mailto:", "tel:", "javascript:", "data:", "file:", "ftp:")):
                continue
            try: target = normalize_url(urljoin(result.final_url, href))
            except Exception: continue
            if self._same_site(target, str(request.start_url), request.include_subdomains):
                rel = {str(item).lower() for item in anchor.get("rel", [])}
                links.append(InternalLink(source_url=normalized, target_url=target, anchor_text=anchor.get_text(" ", strip=True), nofollow="nofollow" in rel, depth=raw.depth))
            else: external += 1
        def add(code, category, severity, evidence, recommendation):
            issues.append(CrawlIssue(code=code, category=category, severity=severity, affected_url=normalized, evidence=evidence, recommendation=recommendation))
        if status is None: add("unreachable", "crawlability", "HIGH", result.error or "No HTTP response", "Retry the crawl and verify server availability.")
        elif status >= 400: add("http_error", "links_status", "HIGH" if status < 500 else "MEDIUM", f"Observed HTTP {status}", "Restore the page or update internal links to a valid destination.")
        if not title: add("missing_title", "metadata", "MEDIUM", "No title element observed", "Add a descriptive page title.")
        elif len(title) < 20 or len(title) > 70: add("title_length_heuristic", "metadata", "LOW", f"Observed title length: {len(title)}", "Review title clarity; this is a Nexora heuristic, not a Google rule.")
        if not description: add("missing_meta_description", "metadata", "LOW", "No meta description observed", "Add a useful description where appropriate.")
        if not h1s: add("missing_h1", "content_structure", "MEDIUM", "No H1 observed", "Add one clear primary heading where appropriate.")
        elif len(h1s) > 1: add("multiple_h1", "content_structure", "LOW", f"Observed {len(h1s)} H1 elements", "Review heading hierarchy.")
        if words == 0: add("empty_content", "content_structure", "HIGH", "No visible words observed", "Verify that meaningful content is available in fetched HTML.")
        elif words < 200: add("thin_content_heuristic", "content_structure", "LOW", f"Observed {words} words", "Review whether the page satisfies its purpose; this is a Nexora heuristic.")
        if images and missing_alt: add("missing_image_alt", "content_structure", "LOW", f"{missing_alt} of {len(images)} images lack non-empty alt text", "Add appropriate alternative text or mark decorative images accordingly.")
        if "noindex" in robots: indexability = IndexabilitySignal.NON_INDEXABLE
        elif status is None or (status and status >= 400): indexability = IndexabilitySignal.ERROR
        elif canonical and canonical != normalized: indexability = IndexabilitySignal.CANONICALIZED
        elif status and 200 <= status < 300: indexability = IndexabilitySignal.INDEXABLE
        else: indexability = IndexabilitySignal.UNKNOWN
        if "noindex" in robots: add("noindex_signal", "indexability", "MEDIUM", robots, "Confirm the noindex directive is intentional.")
        if not canonical: add("missing_canonical_evidence", "indexability", "LOW", "No canonical link observed", "Review whether a canonical declaration is appropriate for this page.")
        elif len(canonical_tags) > 1: add("multiple_canonical", "indexability", "HIGH", f"Observed {len(canonical_tags)} canonical tags", "Declare at most one unambiguous canonical target.")
        page = CrawledPage(url=result.requested_url, normalized_url=normalized, status_code=status, content_type=result.content_type, title=title, meta_description=description, h1s=h1s, canonical=canonical, robots=robots, indexability=indexability, word_count=words, internal_links=len(links), external_links=external, image_count=len(images), missing_alt_count=missing_alt, structured_data_types=self._schema_types(soup), depth=raw.depth, discovered_from=raw.discovered_from, outlink_count=len(links), issues=tuple(issue.code for issue in issues), error=result.error)
        return page, links, issues

    async def run(self, request: SiteCrawlRequest) -> SiteCrawl:
        started = datetime.now(UTC); raw_pages = await self._crawler.crawl(request)
        pages, links, issues, redirects = [], [], [], []
        for raw in raw_pages:
            page, page_links, page_issues = self._analyze_raw(raw, request); pages.append(page); links.extend(page_links); issues.extend(page_issues); redirects.extend(raw.result.redirects)
        status_by_url = {page.normalized_url: page.status_code for page in pages}
        redirect_sources = {edge.source_url for edge in redirects}
        inlinks = Counter(link.target_url for link in links)
        rebuilt_links = []
        for link in links:
            status, issue = status_by_url.get(link.target_url), None
            if status is not None and status >= 400: issue = "BROKEN_INTERNAL_LINK"
            elif link.target_url in redirect_sources: issue = "LINKS_TO_REDIRECT"
            rebuilt_links.append(link.model_copy(update={"target_status": status, "issue": issue}))
            if issue:
                issues.append(CrawlIssue(code=issue.lower(), category="links_status", severity="HIGH" if issue.startswith("BROKEN") else "MEDIUM", affected_url=link.source_url, evidence=f"Internal target: {link.target_url}", recommendation="Update the internal link to a valid final destination."))
        pages = [page.model_copy(update={"inlink_count": inlinks[page.normalized_url]}) for page in pages]
        generic_anchors = {"click here", "read more", "learn more", "more", "here"}
        anchor_counts = Counter(link.anchor_text.strip().casefold() for link in rebuilt_links)
        for link in rebuilt_links:
            anchor = link.anchor_text.strip()
            if not anchor:
                issues.append(CrawlIssue(code="empty_anchor", category="internal_linking", severity="LOW", affected_url=link.source_url, evidence=f"Link to {link.target_url} has no observed text", recommendation="Provide accessible, descriptive link text where appropriate."))
            elif anchor.casefold() in generic_anchors:
                issues.append(CrawlIssue(code="generic_anchor", category="internal_linking", severity="LOW", affected_url=link.source_url, evidence=f"Observed generic anchor: {anchor}", recommendation="Use context-specific anchor text where it improves clarity."))
        for anchor, count in anchor_counts.items():
            if anchor and count >= 5:
                issues.append(CrawlIssue(code="repeated_anchor_observation", category="internal_linking", severity="LOW", affected_url=str(request.start_url), evidence=f"Anchor '{anchor}' appeared {count} times", recommendation="Review repetition for clarity; repetition alone is not classified as spam."))
        for page in pages:
            canonical_status = status_by_url.get(page.canonical) if page.canonical else None
            if canonical_status is not None and canonical_status >= 400:
                issues.append(CrawlIssue(code="canonical_target_error", category="indexability", severity="HIGH", affected_url=page.normalized_url, evidence=f"Canonical target returned HTTP {canonical_status}", recommendation="Point the canonical declaration to a valid intended URL."))
            if page.canonical and not self._same_site(page.canonical, str(request.start_url), request.include_subdomains):
                issues.append(CrawlIssue(code="external_canonical_observation", category="indexability", severity="LOW", affected_url=page.normalized_url, evidence=f"Canonical points to external URL: {page.canonical}", recommendation="Confirm that the external canonical target is intentional."))
        issue_codes_by_url = defaultdict(set)
        for issue in issues:
            issue_codes_by_url[issue.affected_url].add(issue.code)
        pages = [page.model_copy(update={"issues": tuple(sorted(issue_codes_by_url[page.normalized_url]))}) for page in pages]
        title_groups, meta_groups, h1_groups = defaultdict(list), defaultdict(list), defaultdict(list)
        for page in pages:
            if page.title: title_groups[page.title.casefold()].append(page.normalized_url)
            if page.meta_description: meta_groups[page.meta_description.casefold()].append(page.normalized_url)
            if page.h1s: h1_groups[page.h1s[0].casefold()].append(page.normalized_url)
        duplicate_title_urls = {url for urls in title_groups.values() if len(urls) > 1 for url in urls}
        for code, groups, recommendation in (("duplicate_title", title_groups, "Differentiate page titles where pages serve distinct purposes."), ("duplicate_meta_description", meta_groups, "Differentiate descriptions where useful."), ("duplicate_h1", h1_groups, "Review repeated primary headings across distinct pages.")):
            for value, urls in groups.items():
                if len(urls) > 1:
                    for url in urls: issues.append(CrawlIssue(code=code, category="metadata" if "h1" not in code else "content_structure", severity="LOW", affected_url=url, evidence=f"Same value observed on {len(urls)} crawled pages", recommendation=recommendation))
        evidence = await self._evidence_loader(str(request.start_url)) if self._evidence_loader else {}
        gsc, ga4, ranks = evidence.get("gsc", {}), evidence.get("ga4", {}), evidence.get("ranks", {})
        page_urls = {p.normalized_url for p in pages}; opportunities = []
        for page in pages:
            signals, provenance, priority = [], [], 20
            if page.depth > 3: signals.append(f"Observed click depth {page.depth}"); priority += 20
            if page.inlink_count <= 1 and page.depth > 0: signals.append(f"Only {page.inlink_count} crawled inlinks"); priority += 20
            if page.normalized_url in gsc: signals.append(f"Persisted GSC impressions: {gsc[page.normalized_url]}"); provenance.append("GSC"); priority += 15
            if page.normalized_url in ga4: signals.append(f"Persisted GA4 sessions: {ga4[page.normalized_url]}"); provenance.append("GA4"); priority += 15
            if page.normalized_url in ranks: signals.append(f"Tracked SERP position: {ranks[page.normalized_url]}"); provenance.append("RANK_TRACKING"); priority += 20
            if signals and (page.inlink_count <= 1 or page.depth > 3): opportunities.append(LinkOpportunity(priority=min(priority, 100), target_url=page.normalized_url, evidence=tuple(signals), suggested_action="Consider adding contextual internal links from relevant, highly linked internal pages.", provenance=tuple(provenance or ["CRAWL"])))
        for url in sorted(set(gsc) - page_urls): opportunities.append(LinkOpportunity(priority=60, target_url=url, evidence=("Persisted GSC page was not found in this bounded crawl",), suggested_action="Verify crawl reachability and internal discovery paths.", provenance=("GSC", "CRAWL")))
        broken = sum(link.issue == "BROKEN_INTERNAL_LINK" for link in rebuilt_links)
        stats = CrawlStatistics(pages_crawled=len(pages), indexable_signals=sum(p.indexability == IndexabilitySignal.INDEXABLE for p in pages), broken_links=broken, redirects=len(redirects), internal_links=len(rebuilt_links), no_crawled_inlinks=sum(p.depth > 0 and p.inlink_count == 0 for p in pages), depth_four_plus=sum(p.depth >= 4 for p in pages), duplicate_titles=len(duplicate_title_urls), missing_meta=sum(not p.meta_description for p in pages))
        categories = {"Crawlability": 100.0, "Indexability Signals": 100.0, "Metadata": 100.0, "Content Structure": 100.0, "Internal Linking": 100.0, "Links/Status": 100.0, "Structured Data": 100.0}
        mapping = {"crawlability":"Crawlability", "indexability":"Indexability Signals", "metadata":"Metadata", "content_structure":"Content Structure", "internal_linking":"Internal Linking", "links_status":"Links/Status"}
        deduction = {"HIGH": 15, "MEDIUM": 8, "LOW": 3}
        for issue in issues:
            category = mapping.get(issue.category)
            if category: categories[category] = max(0.0, categories[category] - deduction.get(issue.severity, 3))
        if pages and not any(p.structured_data_types for p in pages): categories["Structured Data"] = 70.0
        summary = TechnicalSiteSummary(overall_score=sum(categories.values()) / len(categories), category_scores=categories, statistics=stats)
        crawl = SiteCrawl(request=request, started_at=started, completed_at=datetime.now(UTC), pages=tuple(pages), links=tuple(rebuilt_links), redirects=tuple(redirects), issues=tuple(issues), opportunities=tuple(sorted(opportunities, key=lambda x:(-x.priority,x.target_url))), summary=summary)
        await self._repository.save(crawl); return crawl

    async def latest(self, start_url: str | None = None) -> SiteCrawl | None: return await self._repository.latest(start_url)
    async def history(self, start_url: str | None = None) -> list[SiteCrawl]: return await self._repository.history(start_url)

    @staticmethod
    def compare(current: SiteCrawl, previous: SiteCrawl | None) -> CrawlComparison:
        if previous is None: return CrawlComparison(current_crawl_id=current.crawl_id)
        cp, pp = {p.normalized_url:p for p in current.pages}, {p.normalized_url:p for p in previous.pages}
        ci, pi = {(i.code,i.affected_url) for i in current.issues}, {(i.code,i.affected_url) for i in previous.issues}
        shared = set(cp) & set(pp)
        return CrawlComparison(current_crawl_id=current.crawl_id, previous_crawl_id=previous.crawl_id, new_pages=tuple(sorted(set(cp)-set(pp))), missing_pages=tuple(sorted(set(pp)-set(cp))), new_issues=tuple(sorted(f"{c}: {u}" for c,u in ci-pi)), resolved_issues=tuple(sorted(f"{c}: {u}" for c,u in pi-ci)), status_changes=tuple(sorted(url for url in shared if cp[url].status_code != pp[url].status_code)), metadata_changes=tuple(sorted(url for url in shared if (cp[url].title,cp[url].meta_description)!=(pp[url].title,pp[url].meta_description))), inlink_changes=tuple(sorted(url for url in shared if cp[url].inlink_count != pp[url].inlink_count)), depth_changes=tuple(sorted(url for url in shared if cp[url].depth != pp[url].depth)))

    async def aclose(self) -> None: await self._crawler.aclose()
