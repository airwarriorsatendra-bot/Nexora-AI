from __future__ import annotations

import tempfile
import unittest
from collections import deque
from pathlib import Path
from typing import Any
from types import SimpleNamespace
from decimal import Decimal
from uuid import uuid4

import httpx
from streamlit.testing.v1 import AppTest

from src.ai_visibility.citation_intelligence import CitationHistoryState, CitationIntelligenceService
from src.ai_visibility.composition import AIVisibilityComposition, AIVisibilitySettings
from src.ai_visibility.domain import MonitoredPrompt, PromptCategory, VisibilityRequest
from src.ai_visibility.grounded_providers import GeminiGroundedProvider, PerplexitySonarGroundedProvider, OpenAIGroundedProvider, ClaudeGroundedProvider
from src.content_intelligence.domain import ContentBrief,ContentMode,ContentPriority,ContentScore,SearchIntent
from src.ai_visibility.service import AIVisibilityService
from src.core.exceptions import ExternalAPIError


class Response:
    def __init__(self, payload: Any = None, error: Exception | None = None): self.payload, self.error = payload, error
    def raise_for_status(self):
        if self.error: raise self.error
    def json(self): return self.payload


class Client:
    def __init__(self, outcomes, calls, exits): self.outcomes, self.calls, self.exits = outcomes, calls, exits
    async def __aenter__(self): return self
    async def __aexit__(self, *args): self.exits.append(True)
    async def post(self, url, *, json):
        self.calls.append((url, json)); outcome = self.outcomes.popleft()
        if isinstance(outcome, Exception): raise outcome
        return outcome


class Factory:
    def __init__(self, outcomes): self.outcomes, self.calls, self.exits, self.options = deque(outcomes), [], [], []
    def __call__(self, **kwargs): self.options.append(kwargs); return Client(self.outcomes, self.calls, self.exits)


def request():
    return VisibilityRequest(prompt=MonitoredPrompt(text="best lingerie brands", category=PromptCategory.COMMERCIAL_INVESTIGATION), brand_name="Veloura", target_domain="velouraintimate.com", competitors={"Competitor": ("competitor.test",)})


class GroundedCitationTests(unittest.IsolatedAsyncioTestCase):
    async def test_gemini_normalizes_only_grounding_metadata(self):
        payload = {"responseId": "safe-id", "candidates": [{"content": {"parts": [{"text": "Veloura https://prose.test"}]}, "groundingMetadata": {"groundingChunks": [{"web": {"uri": "https://www.velouraintimate.com/page#x", "title": "Target"}}, {"web": {"uri": "https://competitor.test/a", "title": "Competitor"}}]}}]}
        factory = Factory([Response(payload)]); provider = GeminiGroundedProvider("secret", "gemini-test", http_client_factory=factory)
        response = await provider.run_visibility_prompt(request().prompt)
        self.assertEqual([c.url for c in response.citations], ["https://www.velouraintimate.com/page#x", "https://competitor.test/a"])
        self.assertNotIn("prose.test", " ".join(c.url for c in response.citations)); self.assertEqual(len(factory.exits), 1)
        self.assertIn("google_search", factory.calls[0][1]["tools"][0]); self.assertNotIn("secret", str(response))

    async def test_perplexity_sonar_is_distinct_from_search_adapter(self):
        factory = Factory([Response({"id": "r", "choices": [{"message": {"content": "Grounded answer"}}], "citations": ["https://source.test/a"], "search_results": [{"url": "https://source.test/a", "title": "Source"}]})])
        provider = PerplexitySonarGroundedProvider("secret", "sonar", http_client_factory=factory)
        response = await provider.run_visibility_prompt(request().prompt)
        self.assertEqual(response.provider, "PERPLEXITY_SONAR_API"); self.assertEqual(response.citations[0].title, "Source")
        self.assertEqual(factory.calls[0][0], "https://api.perplexity.ai/chat/completions")

    async def test_openai_and_claude_grounded_metadata(self):
        openai=OpenAIGroundedProvider("secret","gpt",http_client_factory=Factory([Response({"id":"o","output":[{"content":[{"type":"output_text","text":"Answer","annotations":[{"type":"url_citation","url":"https://source.test/a","title":"Source"}]}]}]})]));oresponse=await openai.run_visibility_prompt(request().prompt);self.assertEqual(oresponse.provider,"OPENAI_GROUNDED_API");self.assertEqual(oresponse.citations[0].url,"https://source.test/a")
        claude=ClaudeGroundedProvider("secret","claude",http_client_factory=Factory([Response({"id":"c","content":[{"type":"web_search_tool_result","content":[{"type":"web_search_result","url":"https://source.test/b","title":"Source B"}]},{"type":"text","text":"Answer","citations":[{"type":"web_search_result_location","url":"https://source.test/b","title":"Source B"}]}]})]));cresponse=await claude.run_visibility_prompt(request().prompt);self.assertEqual(cresponse.provider,"CLAUDE_GROUNDED_API");self.assertEqual(len(cresponse.citations),1)

    async def test_client_errors_one_attempt_and_transients_bounded(self):
        for status in (400, 401, 403, 404, 422):
            req = httpx.Request("POST", "https://safe.test"); err = httpx.HTTPStatusError("failure", request=req, response=httpx.Response(status, request=req)); factory = Factory([Response(error=err)])
            with self.assertRaises(ExternalAPIError) as raised: await GeminiGroundedProvider("secret", "model", http_client_factory=factory).run_visibility_prompt(request().prompt)
            self.assertEqual(len(factory.calls), 1); self.assertIs(raised.exception.__cause__, err); self.assertNotIn("secret", str(raised.exception))
        for status in (429, 500, 502, 503, 504):
            req = httpx.Request("POST", "https://safe.test"); err = httpx.HTTPStatusError("failure", request=req, response=httpx.Response(status, request=req)); factory = Factory([Response(error=err)] * 3)
            async def sleep(_): pass
            with self.assertRaises(ExternalAPIError): await GeminiGroundedProvider("secret", "model", http_client_factory=factory, sleep=sleep).run_visibility_prompt(request().prompt)
            self.assertEqual(len(factory.calls), 3); self.assertEqual(len(factory.exits), 3)

    async def test_timeout_bounded_cleanup_and_chaining(self):
        error = httpx.TimeoutException("private transport detail"); factory = Factory([error, error, error])
        async def sleep(_): pass
        with self.assertRaises(ExternalAPIError) as raised: await PerplexitySonarGroundedProvider("secret", "sonar", http_client_factory=factory, sleep=sleep).run_visibility_prompt(request().prompt)
        self.assertIs(raised.exception.__cause__, error); self.assertEqual(len(factory.calls), 3); self.assertEqual(len(factory.exits), 3); self.assertNotIn("secret", str(raised.exception))

    async def test_normalization_matching_coverage_stability_and_history(self):
        payload = {"choices": [{"message": {"content": "Veloura and Competitor"}}], "citations": ["HTTPS://WWW.VELOURAINTIMATE.COM:443/page/#fragment", "https://www.velouraintimate.com/page", "https://sub.competitor.test/x", "https://other.test/x"]}
        provider = PerplexitySonarGroundedProvider("key", "sonar", http_client_factory=Factory([Response(payload), Response(payload)]))
        service = AIVisibilityService(); one = await service.observe(uuid4(), request(), provider); two = await service.observe(one.run_id, request(), provider)
        self.assertTrue(one.target_domain_cited); self.assertEqual(one.target_urls_cited, ("https://www.velouraintimate.com/page",)); self.assertEqual(len(one.citations), 3); self.assertEqual(one.citations[1].competitor, "Competitor")
        intelligence = CitationIntelligenceService(); coverage = intelligence.target_coverage((one, two)); self.assertEqual((coverage.numerator, coverage.denominator, coverage.coverage), (2, 2, 1.0))
        self.assertEqual(intelligence.stability((one, two))[0].sample_size, 2); self.assertEqual(intelligence.history_state((one, two)), CitationHistoryState.CONSISTENT_CITATION)

    async def test_composition_is_additive_and_repository_round_trips(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = AIVisibilitySettings.from_environment({"DATABASE_URL": str(Path(directory) / "v.db"), "GROUNDED_AI_PROVIDER": "perplexity", "PERPLEXITY_API_KEY": "key", "GROUNDED_AI_MODEL": "sonar"})
            app = AIVisibilityComposition(settings).build(); self.assertEqual(app.providers[0].capability.provider, "PERPLEXITY_SONAR_API"); await app.aclose()

    async def test_explicit_prompt_promotion_is_bounded_deduplicated_and_offline(self):
        with tempfile.TemporaryDirectory() as directory:
            app=AIVisibilityComposition(AIVisibilitySettings(Path(directory)/"v.db"),[]).build();items=[("GSC_HIGH_IMPRESSION","example.test",f"query {i}",None) for i in range(30)];promoted=await app.promote_candidates(items,25);self.assertEqual(len(promoted),25);again=await app.promote_candidates(items[:1]);self.assertEqual(promoted[0].prompt_id,again[0].prompt_id);self.assertEqual(promoted[0].source,"GSC_HIGH_IMPRESSION");await app.aclose()

    async def test_page_enrichment_and_content_brief_handoff(self):
        payload={"choices":[{"message":{"content":"Veloura"}}],"citations":["https://velouraintimate.com/page"]};observation=await AIVisibilityService().observe(uuid4(),request(),PerplexitySonarGroundedProvider("key","sonar",http_client_factory=Factory([Response(payload)])))
        readiness=SimpleNamespace(url="https://velouraintimate.com/page",aeo=SimpleNamespace(total=80),geo=SimpleNamespace(total=85));uncited=SimpleNamespace(url="https://velouraintimate.com/uncited",aeo=SimpleNamespace(total=75),geo=SimpleNamespace(total=90));page_gap=SimpleNamespace(target_page="https://velouraintimate.com/page",gsc_clicks=10,gsc_impressions=100,gsc_ctr=Decimal("0.1"));query_gap=SimpleNamespace(mapped_page="https://velouraintimate.com/page",gsc_average_position=Decimal("4.5"),target_position=3,gsc_clicks=10,gsc_impressions=100);crawl=SimpleNamespace(normalized_url="https://velouraintimate.com/page",depth=2,inlink_count=7,issues=("missing_meta",));brief=ContentBrief(target_url="https://velouraintimate.com/page",mode=ContentMode.OPTIMIZE_EXISTING_PAGE,primary_query="query",primary_query_reason="evidence",priority=ContentPriority.HIGH,score=ContentScore(total=50),intent=SearchIntent.INFORMATIONAL,suggested_h1="Heading")
        service=CitationIntelligenceService();pages=service.enrich_pages((observation,),"velouraintimate.com",readiness_pages=(readiness,uncited),page_gaps=(page_gap,),keyword_gaps=(query_gap,),crawl_pages=(crawl,),briefs=(brief,));page=next(x for x in pages if x.target_url.endswith("/page"));not_cited=next(x for x in pages if x.target_url.endswith("/uncited"));self.assertEqual((page.aeo_readiness,page.geo_readiness,page.gsc_average_position,page.tracked_serp_position),(80,85,Decimal("4.5"),3));self.assertTrue(page.content_brief_available);self.assertEqual(page.crawl_depth,2);self.assertEqual(not_cited.geo_citation_state.value,"HIGH_NOT_CITED")
        foreign=service.enrich_pages((observation,),"foreign.test",readiness_pages=(readiness,));self.assertFalse(foreign)
        before=brief.score;attached=service.attach_to_brief(brief,service.gap_evidence(observation));self.assertEqual(attached.score,before);self.assertIn("GROUNDED_CITATION_OBSERVATION",attached.evidence[-1].source);self.assertNotIn(observation.response_text,attached.evidence[-1].observation)

    def test_url_normalization_preserves_meaningful_query(self):
        normalize = AIVisibilityService.normalize_url
        self.assertEqual(normalize("HTTPS://Example.COM:443/a/?x=1#fragment"), "https://example.com/a?x=1")
        self.assertNotEqual(normalize("https://example.com/a?x=1"), normalize("https://example.com/a?x=2"))
        self.assertEqual(normalize("javascript:alert(1)"), "")

    async def test_grounded_dashboard_renders_history_without_calls(self):
        payload = {"choices": [{"message": {"content": "Veloura"}}], "citations": ["https://velouraintimate.com/page"]}
        provider = PerplexitySonarGroundedProvider("key", "sonar", http_client_factory=Factory([Response(payload)]))
        observation = await AIVisibilityService().observe(uuid4(), request(), provider)
        class Workflow:
            calls = 0
            async def providers(self): return [provider.capability]
            async def prompts(self): return [request().prompt]
            async def candidates(self): return []
            async def history(self): return [observation]
            async def run(self, *args): self.calls += 1
            async def add_prompt(self, text): return request().prompt
        def render(workflow):
            from dashboard.ai_visibility import render_ai_visibility
            render_ai_visibility(workflow)
        workflow = Workflow(); view = AppTest.from_function(render, args=(workflow,)).run(timeout=30)
        self.assertFalse(view.exception); self.assertEqual(workflow.calls, 0)
        self.assertEqual(view.metric[0].value, "1"); self.assertEqual(view.metric[1].value, "100.0%")
        self.assertTrue(any("velouraintimate.com/page" in frame.value.to_csv(index=False) for frame in view.dataframe))
        labels={button.label for button in view.download_button};self.assertTrue({"Target citations CSV","Competitor citations CSV","Citation history CSV","Source domains CSV","Grounded report"}.issubset(labels))
