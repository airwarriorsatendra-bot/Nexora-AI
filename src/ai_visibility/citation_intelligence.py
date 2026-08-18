"""Deterministic aggregation for grounded AI citation observations."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from enum import Enum
from decimal import Decimal
import csv
import io

from pydantic import ConfigDict

from src.ai_visibility.domain import AIVisibilityObservation, ObservationState
from src.shared.base.base_model import NexoraModel


class CitationHistoryState(str, Enum):
    NEW_CITATION = "NEW_CITATION"
    CONSISTENT_CITATION = "CONSISTENT_CITATION"
    LOST_CITATION = "LOST_CITATION"
    INTERMITTENT_CITATION = "INTERMITTENT_CITATION"
    NOT_CITED = "NOT_CITED"


class CitationCoverage(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    numerator: int
    denominator: int
    coverage: float | None


class CitationStability(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    prompt: str
    provider: str
    model: str
    citations: int
    sample_size: int
    stability: float


class SourceDomainSummary(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    domain: str
    classification: str
    prompts_cited: int
    citation_count: int
    providers: tuple[str, ...]
    models: tuple[str, ...]
    categories: tuple[str, ...]
    first_seen: datetime
    last_seen: datetime


class ReadinessCitationState(str, Enum):
    HIGH_AND_CITED = "HIGH_AND_CITED"
    HIGH_NOT_CITED = "HIGH_NOT_CITED"
    LOW_AND_CITED = "LOW_AND_CITED"
    LOW_NOT_CITED = "LOW_NOT_CITED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class PageCitationIntelligence(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    target_url: str
    citation_count: int
    prompts_cited: int
    providers: tuple[str, ...]
    models: tuple[str, ...]
    aeo_readiness: int | None = None
    geo_readiness: int | None = None
    aeo_citation_state: ReadinessCitationState = ReadinessCitationState.INSUFFICIENT_EVIDENCE
    geo_citation_state: ReadinessCitationState = ReadinessCitationState.INSUFFICIENT_EVIDENCE
    gsc_clicks: int | None = None
    gsc_impressions: int | None = None
    gsc_ctr: Decimal | None = None
    gsc_average_position: Decimal | None = None
    tracked_serp_position: int | None = None
    crawl_depth: int | None = None
    inlink_count: int | None = None
    technical_issues: tuple[str, ...] = ()
    content_brief_available: bool = False


class CitationGapEvidence(NexoraModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    prompt: str
    provider: str
    model: str
    observed_at: datetime
    target_cited: bool
    target_urls_cited: tuple[str, ...] = ()
    competitor_domains_cited: tuple[str, ...] = ()
    other_source_domains: tuple[str, ...] = ()
    citation_stability: float | None = None
    citation_coverage: float | None = None


class CitationIntelligenceService:
    @staticmethod
    def successful_capable(observations):
        return tuple(o for o in observations if o.state == ObservationState.SUCCESS and o.citation_tracking_available)

    def target_coverage(self, observations) -> CitationCoverage:
        capable = self.successful_capable(observations)
        numerator = sum(o.target_domain_cited is True for o in capable)
        return CitationCoverage(numerator=numerator, denominator=len(capable), coverage=numerator / len(capable) if capable else None)

    def competitor_coverage(self, observations, competitor: str) -> CitationCoverage:
        capable = self.successful_capable(observations)
        numerator = sum(any(c.competitor == competitor for c in o.citations) for o in capable)
        return CitationCoverage(numerator=numerator, denominator=len(capable), coverage=numerator / len(capable) if capable else None)

    def stability(self, observations) -> tuple[CitationStability, ...]:
        groups: dict[tuple[str, str, str], list[AIVisibilityObservation]] = defaultdict(list)
        for item in self.successful_capable(observations):
            groups[(item.prompt, item.provider, item.model)].append(item)
        return tuple(
            CitationStability(prompt=key[0], provider=key[1], model=key[2], citations=sum(o.target_domain_cited is True for o in items), sample_size=len(items), stability=sum(o.target_domain_cited is True for o in items) / len(items))
            for key, items in sorted(groups.items())
        )

    def source_domains(self, observations, target_domain: str = "", competitors: dict[str, tuple[str, ...]] | None = None) -> tuple[SourceDomainSummary, ...]:
        groups = defaultdict(list); competitors = competitors or {}; target = target_domain.casefold().removeprefix("www.")
        for observation in self.successful_capable(observations):
            for citation in observation.citations: groups[citation.domain].append((observation, citation))
        summaries = []
        for domain, rows in sorted(groups.items()):
            competitor = next((name for name, aliases in competitors.items() if any(domain == alias.casefold().removeprefix("www.") or domain.endswith("." + alias.casefold().removeprefix("www.")) for alias in aliases)), None)
            classification = "TARGET" if target and (domain == target or domain.endswith("." + target)) else "CONFIGURED_COMPETITOR" if competitor else "OTHER_SOURCE"
            observations_for_domain = [row[0] for row in rows]
            summaries.append(SourceDomainSummary(domain=domain, classification=classification, prompts_cited=len({o.prompt_id for o in observations_for_domain}), citation_count=len(rows), providers=tuple(sorted({o.provider for o in observations_for_domain})), models=tuple(sorted({o.model for o in observations_for_domain})), categories=tuple(sorted({o.category.value for o in observations_for_domain})), first_seen=min(o.observed_at for o in observations_for_domain), last_seen=max(o.observed_at for o in observations_for_domain)))
        return tuple(summaries)

    def history_state(self, compatible_observations) -> CitationHistoryState:
        items = tuple(sorted(self.successful_capable(compatible_observations), key=lambda o: o.observed_at))
        if not items or not any(o.target_domain_cited for o in items): return CitationHistoryState.NOT_CITED
        if len(items) == 1: return CitationHistoryState.NEW_CITATION
        values = tuple(bool(o.target_domain_cited) for o in items)
        if all(values): return CitationHistoryState.CONSISTENT_CITATION
        if values[-1] and not values[-2]: return CitationHistoryState.NEW_CITATION
        if not values[-1] and values[-2]: return CitationHistoryState.LOST_CITATION
        return CitationHistoryState.INTERMITTENT_CITATION

    @staticmethod
    def readiness_state(score: int | None, cited: bool) -> ReadinessCitationState:
        if score is None: return ReadinessCitationState.INSUFFICIENT_EVIDENCE
        return ReadinessCitationState.HIGH_AND_CITED if score >= 70 and cited else ReadinessCitationState.HIGH_NOT_CITED if score >= 70 else ReadinessCitationState.LOW_AND_CITED if cited else ReadinessCitationState.LOW_NOT_CITED

    def enrich_pages(self, observations, target_domain: str, *, readiness_pages=(), page_gaps=(), keyword_gaps=(), crawl_pages=(), briefs=()) -> tuple[PageCitationIntelligence, ...]:
        host = target_domain.casefold().removeprefix("www."); cited = self.successful_capable(observations); grouped = defaultdict(list)
        for observation in cited:
            for citation in observation.citations:
                if citation.is_target and (citation.domain == host or citation.domain.endswith("." + host)): grouped[citation.normalized_url or citation.url].append((observation, citation))
        normal = lambda value: self._normalize(value)
        readiness = {normal(p.url): p for p in readiness_pages if normal(p.url)}; gaps = {normal(p.target_page): p for p in page_gaps if normal(p.target_page)}; query_gaps=defaultdict(list)
        for item in keyword_gaps:
            mapped=normal(item.mapped_page) if item.mapped_page else ""
            if mapped:query_gaps[mapped].append(item)
        crawls = {normal(p.normalized_url): p for p in crawl_pages if normal(p.normalized_url)}; brief_urls = {normal(b.target_url) for b in briefs if getattr(b, "target_url", None)}
        result=[];all_urls=set(grouped)|set(readiness)|set(gaps)|set(query_gaps)|set(crawls)|brief_urls
        for url in sorted(all_urls):
            rows=grouped.get(url,[])
            if self._host(url) != host: continue
            ready=readiness.get(url);gap=gaps.get(url);queries=query_gaps.get(url,[]);crawl=crawls.get(url);is_cited=bool(rows);aeo=ready.aeo.total if ready else None;geo=ready.geo.total if ready else None;gsc_positions=[q.gsc_average_position for q in queries if q.gsc_average_position is not None];tracked=[q.target_position for q in queries if q.target_position is not None]
            result.append(PageCitationIntelligence(target_url=url,citation_count=len(rows),prompts_cited=len({o.prompt_id for o,_ in rows}),providers=tuple(sorted({o.provider for o,_ in rows})),models=tuple(sorted({o.model for o,_ in rows})),aeo_readiness=aeo,geo_readiness=geo,aeo_citation_state=self.readiness_state(aeo,is_cited),geo_citation_state=self.readiness_state(geo,is_cited),gsc_clicks=gap.gsc_clicks if gap else sum(q.gsc_clicks or 0 for q in queries) if queries else None,gsc_impressions=gap.gsc_impressions if gap else sum(q.gsc_impressions or 0 for q in queries) if queries else None,gsc_ctr=gap.gsc_ctr if gap else None,gsc_average_position=sum(gsc_positions,Decimal())/len(gsc_positions) if gsc_positions else None,tracked_serp_position=min(tracked) if tracked else None,crawl_depth=crawl.depth if crawl else None,inlink_count=crawl.inlink_count if crawl else None,technical_issues=crawl.issues if crawl else (),content_brief_available=url in brief_urls))
        return tuple(result)

    def gap_evidence(self, observation, compatible=()) -> CitationGapEvidence:
        stability = self.stability(tuple(compatible) + (observation,)); matching = next((x for x in stability if x.prompt == observation.prompt and x.provider == observation.provider and x.model == observation.model), None); coverage = self.target_coverage(tuple(compatible) + (observation,))
        return CitationGapEvidence(prompt=observation.prompt,provider=observation.provider,model=observation.model,observed_at=observation.observed_at,target_cited=bool(observation.target_domain_cited),target_urls_cited=observation.target_urls_cited,competitor_domains_cited=tuple(sorted({c.domain for c in observation.citations if c.competitor})),other_source_domains=tuple(sorted({c.domain for c in observation.citations if not c.is_target and not c.competitor})),citation_stability=matching.stability if matching else None,citation_coverage=coverage.coverage)

    @staticmethod
    def attach_to_brief(brief, evidence: CitationGapEvidence):
        from src.content_intelligence.domain import BriefEvidence
        item=BriefEvidence(source="GROUNDED_CITATION_OBSERVATION",observation=evidence.model_dump_json())
        return brief.model_copy(update={"evidence":brief.evidence+(item,)})

    def actions(self, observations) -> tuple[str, ...]:
        capable=self.successful_capable(observations);actions=[]
        if any(o.brand_mention and o.target_domain_cited is False for o in capable):actions.append("Brand mention observed without target-domain citation.")
        if any(not o.target_domain_cited and any(c.competitor for c in o.citations) for o in capable):actions.append("Configured competitor citation observed without a target citation; review source support and content differentiation.")
        if any(o.target_urls_cited for o in capable):actions.append("Preserve and monitor cited target content; avoid unnecessary disruptive changes.")
        return tuple(actions)

    @staticmethod
    def _host(value):
        from urllib.parse import urlsplit
        return (urlsplit(value if "://" in value else "//"+value).hostname or "").casefold().removeprefix("www.")

    @staticmethod
    def _normalize(value):
        from src.ai_visibility.service import AIVisibilityService
        return AIVisibilityService.normalize_url(value or "")
