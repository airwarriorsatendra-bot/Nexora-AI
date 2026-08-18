"""Deterministic provider-scoped Backlink Intelligence 2.0 analysis."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

from src.backlinks.domain.backlink import Backlink
from src.backlinks.domain.intelligence import (
    AuthorityBatchPreview, AuthorityHistoryState, AuthorityObservation, AuthorityScope,
    BacklinkProspect, LinkIntersectObservation, ObservedGapState, OutreachHandoff,
    ProspectOpportunityType, ProspectPriority, ScoreBreakdown,
)
from src.backlinks.domain.normalization import canonical_url, normalized_domain
from src.backlinks.domain.opportunity import BacklinkOpportunity
from src.backlinks.providers import AuthorityMetricsProvider
from src.backlinks.repositories.backlink_repository import BacklinkRepository
from src.core.enums import BacklinkVerificationStatus, LinkAttribute
from src.core.exceptions import BacklinkError


class BacklinkIntelligenceService:
    DEFAULT_BATCH = 10
    MAXIMUM_BATCH = 25
    HARD_CEILING = 50

    def __init__(self, repository: BacklinkRepository, authority_provider: AuthorityMetricsProvider | None = None, *, freshness_days: int = 30) -> None:
        self.repository = repository; self.authority_provider = authority_provider; self.freshness_days = max(1, freshness_days)

    async def preview_authority(self, targets: list[str], scope: AuthorityScope = AuthorityScope.URL, *, force: bool = False, maximum: int = MAXIMUM_BATCH) -> AuthorityBatchPreview:
        unique = tuple(dict.fromkeys(self._normalize_target(x, scope) for x in targets))
        if len(unique) > min(maximum, self.HARD_CEILING): raise BacklinkError(f"Authority enrichment is limited to {min(maximum,self.HARD_CEILING)} unique targets.")
        cached = 0
        if not force:
            for target in unique:
                if self._fresh(await self.repository.latest_authority(target, scope)): cached += 1
        return AuthorityBatchPreview(requested=len(targets), unique_targets=len(unique), cached=cached, provider_calls=len(unique)-cached, maximum=min(maximum,self.HARD_CEILING))

    async def enrich_authority(self, targets: list[str], scope: AuthorityScope = AuthorityScope.URL, *, force: bool = False, maximum: int = MAXIMUM_BATCH) -> tuple[AuthorityObservation, ...]:
        preview = await self.preview_authority(targets, scope, force=force, maximum=maximum)
        if preview.provider_calls and self.authority_provider is None: raise BacklinkError("MOZ_API_TOKEN missing; authority enrichment is disabled.")
        unique = tuple(dict.fromkeys(self._normalize_target(x, scope) for x in targets)); results=[]
        for target in unique:
            cached = None if force else await self.repository.latest_authority(target, scope)
            if self._fresh(cached): results.append(cached); continue
            observed = await self.authority_provider.observe(target, scope)  # type: ignore[union-attr]
            await self.repository.save_authority(observed); results.append(observed)
        return tuple(results)

    def score(self, *, relevance: int, contactability: int, authority: AuthorityObservation | None, competitor_gap: bool = False, link_intersect: bool = False, target_page_ready: bool = False, followed: bool | None = None) -> ScoreBreakdown:
        da = authority.domain_authority if authority else None; pa = authority.page_authority if authority else None; spam = authority.spam_score if authority else None
        return ScoreBreakdown(relevance=round(max(0,min(100,relevance))*.25), authority=0 if da is None else round(20*da/100), page_authority=0 if pa is None else round(10*pa/100), risk_adjustment=0 if spam is None or spam < 30 else -min(20,round(spam/5)), competitor_gap=15 if competitor_gap else 0, link_intersect=10 if link_intersect else 0, target_page=10 if target_page_ready else 0, contactability=round(max(0,min(100,contactability))*.1))

    async def prospects(self, opportunities: list[BacklinkOpportunity], *, authority: dict[str, AuthorityObservation] | None = None, relevance: dict[str,int] | None = None, contactability: dict[str,int] | None = None, competitor_domains: set[str] | None = None, target_page: str | None = None) -> tuple[BacklinkProspect,...]:
        authority=authority or {}; relevance=relevance or {}; contactability=contactability or {}; competitor_domains=competitor_domains or set(); output=[]
        type_map={"guest_post":ProspectOpportunityType.GUEST_POST,"resource_page":ProspectOpportunityType.RESOURCE_PAGE,"listicle":ProspectOpportunityType.LISTICLE,"broken_link":ProspectOpportunityType.BROKEN_LINK,"competitor_link":ProspectOpportunityType.COMPETITOR_LINK_GAP}
        for item in opportunities:
            observed=authority.get(item.domain); is_gap=item.domain in competitor_domains; kind=type_map.get(item.opportunity_type.value,ProspectOpportunityType.OTHER_RELEVANT_PROSPECT); breakdown=self.score(relevance=relevance.get(item.domain,50),contactability=contactability.get(item.domain,0),authority=observed,competitor_gap=is_gap,target_page_ready=bool(target_page)); total=breakdown.total; priority=ProspectPriority.CRITICAL if total>=85 else ProspectPriority.HIGH if total>=65 else ProspectPriority.MEDIUM if total>=40 else ProspectPriority.LOW
            prospect=BacklinkProspect(domain=item.domain,representative_url=item.url,opportunity_type=kind,discovery_source=item.source,competitors=(item.domain,) if is_gap else (),target_page=target_page,authority_observation_id=observed.observation_id if observed else None,domain_authority=observed.domain_authority if observed else None,page_authority=observed.page_authority if observed else None,spam_score=observed.spam_score if observed else None,link_propensity=observed.link_propensity if observed else None,relevance=relevance.get(item.domain,50),contactability=contactability.get(item.domain,0),score=total,priority=priority,reasons=tuple(item.evidence)+(f"Deterministic components: {breakdown.model_dump()}",))
            # Keep the authority provenance referenced by the prospect durable. This
            # also makes direct service use safe when callers supply a fresh provider
            # observation that has not previously passed through enrichment.
            if observed is not None:
                await self.repository.save_authority(observed)
            await self.repository.save_prospect(prospect);output.append(prospect)
        return tuple(sorted(output,key=lambda x:(-x.score,x.domain)))

    def link_intersect(self, observations: list[Backlink], target_domain: str, competitor_domains: set[str], authority: dict[str,AuthorityObservation] | None = None) -> tuple[LinkIntersectObservation,...]:
        authority=authority or {}; target=normalized_domain(target_domain); competitors={normalized_domain(x) for x in competitor_domains}; grouped=defaultdict(list)
        for link in observations: grouped[link.source_domain].append(link)
        output=[]
        for source,links in grouped.items():
            targets={x.target_domain for x in links}; seen_comp=tuple(sorted(targets & competitors)); target_seen=target in targets
            if seen_comp and target_seen: state=ObservedGapState.SHARED_OBSERVED
            elif seen_comp: state=ObservedGapState.COMPETITOR_ONLY_OBSERVED
            elif target_seen: state=ObservedGapState.TARGET_ONLY_OBSERVED
            else: state=ObservedGapState.INSUFFICIENT_EVIDENCE
            output.append(LinkIntersectObservation(source_domain=source,representative_urls=tuple(dict.fromkeys(str(x.source_url) for x in links)),competitor_domains=seen_comp,competitor_count=len(seen_comp),target_observed=target_seen,evidence_state=state,authority=authority.get(source),provenance=tuple(sorted({"NEXORA_HTML_VERIFICATION" for _ in links}))))
        return tuple(sorted(output,key=lambda x:(-x.competitor_count,x.source_domain)))

    def authority_change(self, current: AuthorityObservation, previous: AuthorityObservation | None) -> AuthorityHistoryState:
        if current.domain_authority is None:return AuthorityHistoryState.UNAVAILABLE
        if previous is None or previous.domain_authority is None:return AuthorityHistoryState.NEW
        if current.domain_authority>previous.domain_authority:return AuthorityHistoryState.INCREASED
        if current.domain_authority<previous.domain_authority:return AuthorityHistoryState.DECREASED
        return AuthorityHistoryState.STABLE

    @staticmethod
    def cross_source_priority(target_url: str, *, gsc: dict[str, object] | None = None, ga4: dict[str, object] | None = None, rank: dict[str, object] | None = None, competitor_gap: dict[str, object] | None = None, content: dict[str, object] | None = None, crawl: dict[str, object] | None = None) -> tuple[int, bool, tuple[str, ...]]:
        """Combine already-persisted, URL-compatible evidence without causal claims."""
        target = canonical_url(target_url); host = normalized_domain(target); score = 0; reasons=[]; ready=True
        sources=(("GSC",gsc),("GA4",ga4),("RANK",rank),("COMPETITOR_GAP",competitor_gap),("CONTENT",content),("CRAWL",crawl))
        for name,evidence in sources:
            if not evidence: continue
            evidence_url=str(evidence.get("url") or evidence.get("target_url") or "")
            if evidence_url and normalized_domain(evidence_url)!=host: continue
            if name=="GSC" and int(evidence.get("impressions") or 0)>0:score+=15;reasons.append("Persisted GSC demand evidence is available.")
            elif name=="GA4" and int(evidence.get("sessions") or 0)>0:score+=5;reasons.append("Persisted GA4 page engagement context is available; attribution is not claimed.")
            elif name=="RANK" and 4<=int(evidence.get("position") or 0)<=20:score+=15;reasons.append("Tracked SERP position is between 4 and 20.")
            elif name=="COMPETITOR_GAP" and bool(evidence.get("competitors_ahead")):score+=15;reasons.append("Persisted competitor-gap evidence exists.")
            elif name=="CONTENT" and bool(evidence.get("brief_available")):score+=10;reasons.append("A compatible content brief exists.")
            elif name=="CRAWL":
                status=int(evidence.get("status_code") or 0);indexable=bool(evidence.get("indexable",True))
                if status>=400 or not indexable:ready=False;reasons.append("Technical precondition must be resolved before outreach.")
                else:score+=10;reasons.append("Persisted crawl evidence indicates a technically available target page.")
        return min(70,score),ready,tuple(reasons)

    @staticmethod
    def reclamation(backlinks: list[Backlink], target_status: dict[str,int]) -> tuple[dict[str,str],...]:
        actions=[]
        for link in backlinks:
            status=target_status.get(canonical_url(str(link.target_url)))
            if link.status is BacklinkVerificationStatus.LOST: actions.append({"source_url":str(link.source_url),"target_url":str(link.target_url),"evidence":"lost_from_provider_dataset","action":"Confirm the source evidence, then contact the source or restore the relationship."})
            elif status in {404,410}: actions.append({"source_url":str(link.source_url),"target_url":str(link.target_url),"evidence":f"target_http_{status}","action":"Restore the page or redirect to a closely equivalent destination before outreach."})
            elif status and 300<=status<400: actions.append({"source_url":str(link.source_url),"target_url":str(link.target_url),"evidence":f"target_http_{status}","action":"Review the redirect destination and request a direct destination update where appropriate."})
        return tuple(actions)

    @staticmethod
    def anchor_summary(backlinks: list[Backlink], brand: str = "") -> tuple[dict[str,object],...]:
        counts=defaultdict(int)
        for link in backlinks:
            anchor=link.anchor_text.strip(); low=anchor.casefold()
            kind="empty" if not anchor else "url" if low.startswith(("http://","https://","www.")) else "branded" if brand and brand.casefold() in low else "generic" if low in {"click here","learn more","website","source"} else "query_related"
            counts[kind]+=1
        return tuple({"anchor_type":k,"count":v} for k,v in sorted(counts.items()))

    @staticmethod
    def handoff(prospect: BacklinkProspect, authority: AuthorityObservation | None = None) -> OutreachHandoff:
        risk="manual_review" if prospect.spam_score is not None and prospect.spam_score>=30 else "no_high_risk_signal_observed"
        return OutreachHandoff(prospect_id=prospect.prospect_id,domain=prospect.domain,representative_url=prospect.representative_url,target_page=prospect.target_page,opportunity_type=prospect.opportunity_type,authority_evidence=authority,risk=risk,relevance=prospect.relevance,score=prospect.score,priority=prospect.priority,contactability=prospect.contactability,discovery_source=prospect.discovery_source,evidence_summary=prospect.reasons)

    def _fresh(self, value: AuthorityObservation | None) -> bool:
        return value is not None and value.observed_at >= datetime.now(UTC)-timedelta(days=self.freshness_days)
    @staticmethod
    def _normalize_target(value: str, scope: AuthorityScope) -> str:
        return normalized_domain(value) if scope is AuthorityScope.DOMAIN else canonical_url(value)
