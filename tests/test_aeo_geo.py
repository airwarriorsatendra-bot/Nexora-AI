from __future__ import annotations

import unittest
from decimal import Decimal
from uuid import uuid4

from streamlit.testing.v1 import AppTest

from src.aeo_geo.domain import AEOGEOReport, FAQStatus, QuestionType, ReadinessLevel
from src.aeo_geo.service import AEOGEOService
from src.competitor_gap.service import CompetitorGapService
from src.rank_tracking.domain import RankCheck, SERPResult, TrackedKeyword
from src.site_crawl.domain import CrawledPage, IndexabilitySignal


def _gap_report(queries=("how to choose lingerie",), mapped=True):
    keywords, checks, gsc = [], [], {}
    for index, query in enumerate(queries):
        keyword_id = uuid4()
        keyword = TrackedKeyword(keyword_id=keyword_id, keyword=query, target_domain="example.com", target_url="https://example.com/guide" if mapped else None)
        results = (
            SERPResult(position=1, title="Competitor", url="https://competitor.test/guide", domain="competitor.test"),
            SERPResult(position=5, title="Target", url="https://example.com/guide", domain="example.com"),
        )
        keywords.append(keyword)
        checks.append(RankCheck(keyword_id=keyword_id, keyword=query, context=keyword.context, depth=10, provider="offline", target_position=5, results=results))
        gsc[query] = (1000 + index, 50, Decimal("7.2"), Decimal("0.05"))
    return CompetitorGapService().analyze("example.com", keywords, checks, gsc_queries=gsc)


def _page(**updates):
    values = dict(url="https://example.com/guide", normalized_url="https://example.com/guide", status_code=200,
                  content_type="text/html", title="How to choose lingerie", meta_description="A practical guide.",
                  h1s=("How to choose lingerie",), word_count=800, external_links=2,
                  structured_data_types=("FAQPage", "Organization"), depth=1,
                  indexability=IndexabilitySignal.INDEXABLE)
    values.update(updates)
    return CrawledPage(**values)


def _render(workflow):
    from dashboard.aeo_geo import render_aeo_geo
    render_aeo_geo(workflow)


class AEOGEOTests(unittest.TestCase):
    def test_question_detection_and_non_questions(self):
        service = AEOGEOService()
        expected = {"how does it work": QuestionType.HOW, "WHAT IS AEO?": QuestionType.WHAT,
                    "best way to write": QuestionType.BEST_WAY, "red vs blue": QuestionType.VS,
                    "difference between a and b": QuestionType.DIFFERENCE_BETWEEN,
                    "meaning of aeo": QuestionType.MEANING_OF}
        for value, kind in expected.items(): self.assertEqual(service.question_type(value), kind)
        self.assertIsNone(service.question_type("lingerie brands india"))

    def test_strong_readiness_uses_observed_evidence(self):
        report = AEOGEOService().analyze("example.com", _gap_report(), {_page().normalized_url: _page()})
        self.assertEqual(len(report.questions), 1)
        self.assertEqual(report.questions[0].gsc_average_position, Decimal("7.2"))
        page = report.pages[0]
        self.assertEqual(page.aeo_level, ReadinessLevel.STRONG)
        self.assertEqual(page.geo_level, ReadinessLevel.STRONG)
        self.assertEqual(page.faq_status, FAQStatus.FAQ_SCHEMA_OBSERVED)

    def test_weak_and_technical_blocker(self):
        page = _page(status_code=500, indexability=IndexabilitySignal.ERROR, title="", meta_description="", h1s=(), word_count=0, external_links=0, structured_data_types=(), issues=("server_error",))
        report = AEOGEOService().analyze("example.com", _gap_report(), {page.normalized_url: page})
        scored = report.pages[0]
        self.assertEqual(scored.aeo_level, ReadinessLevel.WEAK)
        self.assertEqual(scored.geo_level, ReadinessLevel.WEAK)
        self.assertTrue(scored.recommendations[0].startswith("Resolve"))

    def test_insufficient_page_evidence(self):
        page = CrawledPage(url="https://example.com/guide", normalized_url="https://example.com/guide", depth=1)
        report = AEOGEOService().analyze("example.com", _gap_report(), {page.normalized_url: page})
        self.assertEqual(report.pages[0].aeo_level, ReadinessLevel.INSUFFICIENT_EVIDENCE)
        self.assertEqual(report.pages[0].geo_level, ReadinessLevel.INSUFFICIENT_EVIDENCE)

    def test_multiple_questions_create_cautious_faq_opportunity(self):
        page = _page(h1s=("Lingerie guide",), structured_data_types=())
        report = AEOGEOService().analyze("example.com", _gap_report(("how to choose lingerie", "what is lingerie sizing")), {page.normalized_url: page})
        self.assertEqual(report.pages[0].faq_status, FAQStatus.FAQ_CONTENT_OPPORTUNITY)
        self.assertTrue(any("not guaranteed" in item for item in report.pages[0].recommendations))

    def test_unmapped_question_is_preserved_without_page_claim(self):
        report = AEOGEOService().analyze("example.com", _gap_report(mapped=False), {})
        self.assertEqual(len(report.questions), 1)
        self.assertIsNone(report.questions[0].mapped_page)
        self.assertFalse(report.pages)

    def test_exports_disclose_limits_and_forbid_visibility_claims(self):
        report = AEOGEOService().analyze("example.com", _gap_report(), {_page().normalized_url: _page()})
        payload = report.model_dump_json() + AEOGEOService.markdown(report)
        self.assertIn("not monitored", payload)
        self.assertNotIn("AI visibility score", payload)
        self.assertNotIn("guaranteed citation", payload)

    def test_dashboard_requires_explicit_analysis_and_exports(self):
        report = AEOGEOService().analyze("example.com", _gap_report(), {_page().normalized_url: _page()})
        class Workflow:
            calls = 0
            async def targets(self): return ["example.com"]
            async def analyze(self, target): self.calls += 1; return report
        workflow = Workflow()
        view = AppTest.from_function(_render, args=(workflow,)).run(timeout=30)
        self.assertFalse(view.exception)
        self.assertEqual(workflow.calls, 0)
        next(button for button in view.button if button.label == "Load readiness").click()
        view.run(timeout=30)
        self.assertFalse(view.exception)
        self.assertEqual(workflow.calls, 1)
        self.assertEqual(len(view.metric), 7)
        self.assertEqual(len(view.download_button), 5)
