"""Pure deterministic AEO/GEO readiness analysis over persisted evidence."""
from __future__ import annotations

import re
from collections import defaultdict
from decimal import Decimal

from src.aeo_geo.domain import (
    AEOGEOReport, AEOScoreBreakdown, FAQStatus, GEOScoreBreakdown,
    PageReadiness, QuestionOpportunity, QuestionType, ReadinessLevel,
)
from src.competitor_gap.domain import CompetitorGapReport, KeywordGap
from src.site_crawl.domain import CrawledPage, IndexabilitySignal


class AEOGEOService:
    """Scores readiness signals; it does not observe answer-engine visibility."""

    _PREFIXES = {
        "who": QuestionType.WHO, "what": QuestionType.WHAT, "when": QuestionType.WHEN,
        "where": QuestionType.WHERE, "why": QuestionType.WHY, "how": QuestionType.HOW,
        "which": QuestionType.WHICH, "can": QuestionType.CAN, "does": QuestionType.DOES,
        "is": QuestionType.IS, "are": QuestionType.ARE, "should": QuestionType.SHOULD,
    }

    @classmethod
    def question_type(cls, query: str) -> QuestionType | None:
        value = " ".join(query.casefold().strip().split()).rstrip("?")
        if not value:
            return None
        if value.startswith("best way to "):
            return QuestionType.BEST_WAY
        if value.startswith("difference between "):
            return QuestionType.DIFFERENCE_BETWEEN
        if value.startswith("meaning of "):
            return QuestionType.MEANING_OF
        if re.search(r"\s(?:vs\.?|versus)\s", value):
            return QuestionType.VS
        first = value.split(maxsplit=1)[0]
        return cls._PREFIXES.get(first)

    def analyze(
        self,
        target_domain: str,
        gap_report: CompetitorGapReport,
        crawl_pages: dict[str, CrawledPage],
    ) -> AEOGEOReport:
        questions = self._questions(gap_report.keyword_gaps)
        by_page: dict[str, list[QuestionOpportunity]] = defaultdict(list)
        for item in questions:
            if item.mapped_page in crawl_pages:
                by_page[item.mapped_page].append(item)
        relevant = {url for url in by_page}
        relevant.update(url for url, page in crawl_pages.items() if page.structured_data_types)
        pages = tuple(self._page(crawl_pages[url], by_page[url]) for url in sorted(relevant))
        return AEOGEOReport(
            target_domain=target_domain,
            questions=questions,
            pages=pages,
            notes=(
                "AEO and GEO readiness scores are deterministic Nexora heuristics, not search-ranking or AI-citation guarantees.",
                "Actual AI answer visibility, mentions, citations, and model responses are not monitored or measured.",
                "Full paragraph, H2, list, table, author, and citation-quality extraction is unavailable in the persisted crawl schema.",
            ),
        )

    def _questions(self, gaps: tuple[KeywordGap, ...]) -> tuple[QuestionOpportunity, ...]:
        deduplicated: dict[str, QuestionOpportunity] = {}
        for gap in gaps:
            kind = self.question_type(gap.keyword)
            if kind is None:
                continue
            key = " ".join(gap.keyword.casefold().split())
            evidence = list(gap.evidence[:3])
            if gap.gsc_impressions is not None:
                evidence.append(f"Persisted GSC impressions: {gap.gsc_impressions}.")
            if gap.target_position is not None:
                evidence.append(f"Tracked SERP position: {gap.target_position}.")
            priority = min(100, 25 + min(35, (gap.gsc_impressions or 0) // 100) + min(25, gap.competitors_ahead * 5) + (15 if gap.mapped_page else 0))
            action = {
                QuestionType.HOW: "Consider a concise answer followed by evidence-backed steps on the mapped page.",
                QuestionType.VS: "Consider a factual comparison section; use a table only when the attributes are genuinely comparable.",
                QuestionType.DIFFERENCE_BETWEEN: "Consider a factual comparison section that states the distinction directly.",
            }.get(kind, "Consider answering the question directly on the mapped page using verifiable, source-supported information.")
            candidate = QuestionOpportunity(
                query=gap.keyword, question_type=kind, mapped_page=gap.mapped_page,
                clicks=gap.gsc_clicks, impressions=gap.gsc_impressions, ctr=gap.gsc_ctr,
                gsc_average_position=gap.gsc_average_position,
                tracked_serp_position=gap.target_position, confidence=Decimal("1"), priority_score=priority,
                evidence=tuple(evidence), recommended_action=action,
            )
            prior = deduplicated.get(key)
            if prior is None or candidate.priority_score > prior.priority_score:
                deduplicated[key] = candidate
        return tuple(sorted(deduplicated.values(), key=lambda item: (-item.priority_score, item.query.casefold())))

    def _page(self, page: CrawledPage, questions: list[QuestionOpportunity]) -> PageReadiness:
        schemas = {item.casefold() for item in page.structured_data_types}
        accessible = page.status_code is not None and 200 <= page.status_code < 300 and page.indexability == IndexabilitySignal.INDEXABLE and not page.error
        question_heading = any(self.question_type(h1) is not None for h1 in page.h1s)
        faq = "faqpage" in schemas
        topic = bool(page.title and page.meta_description and page.h1s)
        aeo_parts = {
            "question_coverage": min(20, 8 * len(questions)),
            "direct_answer_structure": 12 if question_heading else 0,
            "faq_schema": 15 if faq else 0,
            "heading_structure": 15 if page.h1s else 0,
            "content_clarity": 15 if topic and page.word_count >= 150 else 8 if page.title or page.h1s else 0,
            "technical_accessibility": 23 if accessible else 0,
        }
        geo_parts = {
            "extractability": 20 if topic and page.word_count >= 150 else 10 if page.h1s else 0,
            "entity_clarity": 15 if schemas.intersection({"organization", "person", "product", "localbusiness"}) else 5 if page.title else 0,
            "source_support": 15 if page.external_links > 0 else 0,
            "structured_data": 15 if schemas else 0,
            "topic_clarity": 15 if topic else 8 if page.title or page.h1s else 0,
            "technical_accessibility": 20 if accessible else 0,
        }
        aeo = AEOScoreBreakdown(**aeo_parts, total=sum(aeo_parts.values()))
        geo = GEOScoreBreakdown(**geo_parts, total=sum(geo_parts.values()))
        observations = [
            f"{len(questions)} persisted question query opportunity/opportunities mapped to this page.",
            f"Structured data observed: {', '.join(page.structured_data_types) if page.structured_data_types else 'none'}.",
            f"External links observed: {page.external_links}; their source quality was not evaluated.",
            "Direct-answer paragraphs, H2s, lists, and tables were not evaluated because those elements are not persisted.",
        ]
        recommendations: list[str] = []
        if not accessible:
            recommendations.append("Resolve observed HTTP, indexability, or crawl errors before content-readiness work.")
        if questions and not question_heading:
            recommendations.append("Consider a clear question-led section with a concise, evidence-backed answer.")
        if len(questions) >= 2 and not faq:
            recommendations.append("Consider an FAQ content block when the questions are genuinely distinct; rich-result eligibility is not guaranteed.")
        if not schemas:
            recommendations.append("Evaluate applicable schema from visible page content; do not add unsupported entities or claims.")
        if not page.external_links:
            recommendations.append("Where factual claims need support, consider citing credible primary sources.")
        return PageReadiness(
            url=page.normalized_url, aeo=aeo, geo=geo,
            aeo_level=self._level(aeo.total, self._has_evidence(page)), geo_level=self._level(geo.total, self._has_evidence(page)),
            faq_status=FAQStatus.FAQ_SCHEMA_OBSERVED if faq else FAQStatus.FAQ_CONTENT_OPPORTUNITY if len(questions) >= 2 else FAQStatus.FAQ_SCHEMA_NOT_OBSERVED,
            question_opportunities=len(questions), structured_data_types=page.structured_data_types,
            observations=tuple(observations), technical_issues=page.issues,
            recommendations=tuple(dict.fromkeys(recommendations)),
        )

    @staticmethod
    def _level(score: int, has_evidence: bool = True) -> ReadinessLevel:
        if not has_evidence: return ReadinessLevel.INSUFFICIENT_EVIDENCE
        if score >= 75: return ReadinessLevel.STRONG
        if score >= 50: return ReadinessLevel.MODERATE
        return ReadinessLevel.WEAK

    @staticmethod
    def _has_evidence(page: CrawledPage) -> bool:
        return any((page.status_code is not None, page.title, page.meta_description, page.h1s, page.word_count, page.structured_data_types, page.issues, page.error))

    @staticmethod
    def markdown(report: AEOGEOReport) -> str:
        lines = ["# Nexora AEO & GEO Readiness Report", "", f"Target: {report.target_domain}", "", "## Important limitations"]
        lines.extend(f"- {note}" for note in report.notes)
        lines.extend(("", "## Page readiness"))
        for page in report.pages:
            lines.extend(("", f"### {page.url}", f"- AEO readiness: {page.aeo.total}/100 ({page.aeo_level.value})", f"- GEO readiness: {page.geo.total}/100 ({page.geo_level.value})"))
            lines.extend(f"- Action: {item}" for item in page.recommendations)
        return "\n".join(lines) + "\n"
