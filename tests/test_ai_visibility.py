from __future__ import annotations
import tempfile,unittest
from pathlib import Path
from uuid import uuid4
import httpx
from streamlit.testing.v1 import AppTest
from src.ai_visibility.composition import AIVisibilityComposition,AIVisibilitySettings
from src.ai_visibility.domain import *
from src.ai_visibility.providers import OfflineVisibilityProvider
from src.ai_visibility.service import AIVisibilityService
def prompt(text="best lingerie brands in India"):return MonitoredPrompt(text=text,category=PromptCategory.CATEGORY_DISCOVERY)
def request(text="best lingerie brands in India"):return VisibilityRequest(prompt=prompt(text),brand_name="Veloura Intimate",brand_aliases=("Veloura",),target_domain="velouraintimate.com",competitors={"Competitor A":("competitor-a.com",),"Competitor B":("competitor-b.com",)})
def render(workflow):
 from dashboard.ai_visibility import render_ai_visibility
 render_ai_visibility(workflow)
class AIVisibilityTests(unittest.IsolatedAsyncioTestCase):
 async def test_mentions_order_alias_punctuation_and_citations(self):
  provider=OfflineVisibilityProvider({request().prompt.text:("Competitor A, VELOURA Intimate, and Competitor B. Veloura is notable.",("https://competitor-a.com/x","https://www.velouraintimate.com/page"))});o=await AIVisibilityService().observe(uuid4(),request(),provider);self.assertEqual(o.state,ObservationState.SUCCESS);self.assertEqual(o.brand_mention.count,2);self.assertEqual(o.brand_mention.mention_order,2);self.assertEqual([m.mention_order for m in o.competitor_mentions],[1,3]);self.assertTrue(o.target_domain_cited)
 async def test_substring_false_positive_and_ungrounded_citation_unavailable(self):
  p=OfflineVisibilityProvider({request().prompt.text:("Prevelourable is unrelated and https://velouraintimate.com is prose.",())},citations_supported=False);o=await AIVisibilityService().observe(uuid4(),request(),p);self.assertIsNone(o.brand_mention);self.assertFalse(o.citation_tracking_available);self.assertIsNone(o.target_domain_cited);self.assertFalse(o.citations)
 async def test_success_absent_is_distinct_from_failure(self):
  p=OfflineVisibilityProvider({request().prompt.text:("Competitor A and Competitor B",())});o=await AIVisibilityService().observe(uuid4(),request(),p);self.assertEqual(o.state,ObservationState.SUCCESS);self.assertIsNone(o.brand_mention)
  class Failure(OfflineVisibilityProvider):
   async def run_visibility_prompt(self,prompt):raise httpx.TimeoutException("secret-safe")
  failed=await AIVisibilityService().observe(uuid4(),request(),Failure());self.assertEqual(failed.state,ObservationState.TIMEOUT);self.assertIsNone(failed.brand_mention)
 async def test_rate_limit_and_empty_response(self):
  class Limited(OfflineVisibilityProvider):
   async def run_visibility_prompt(self,prompt):raise httpx.HTTPStatusError("429",request=httpx.Request("POST","https://example.test"),response=httpx.Response(429))
  self.assertEqual((await AIVisibilityService().observe(uuid4(),request(),Limited())).state,ObservationState.RATE_LIMITED)
  self.assertEqual((await AIVisibilityService().observe(uuid4(),request(),OfflineVisibilityProvider({request().prompt.text:("",())}))).state,ObservationState.EMPTY_RESPONSE)
 async def test_coverage_stability_and_failed_denominator(self):
  service=AIVisibilityService();rid=uuid4();p=OfflineVisibilityProvider({request().prompt.text:("Veloura",("https://velouraintimate.com",))});yes=await service.observe(rid,request(),p);no=(await service.observe(rid,request(),OfflineVisibilityProvider({request().prompt.text:("Other",())})));failed=no.model_copy(update={"state":ObservationState.PROVIDER_ERROR});run=AIVisibilityRun(run_id=rid,brand_name="Veloura Intimate",target_domain="velouraintimate.com",providers=(p.capability.provider,),prompt_count=1,repetitions=3,observations=(yes,no,failed));report=service.report(run);self.assertEqual(report.brand_mention_coverage,.5);self.assertEqual(report.citation_denominator,2);self.assertEqual(report.provider_summaries[0].sample_size,2)
 async def test_history_compatible_provider_model_only(self):
  service=AIVisibilityService();rid=uuid4();p=OfflineVisibilityProvider({request().prompt.text:("Veloura",())});current=await service.observe(rid,request(),p);old=current.model_copy(update={"brand_mention":None});self.assertEqual(service.changes((current,),(old,))[0][1],VisibilityChange.NEWLY_VISIBLE);different=old.model_copy(update={"model":"other"});self.assertEqual(service.changes((current,),(different,))[0][1],VisibilityChange.NEWLY_VISIBLE)
 async def test_repository_composition_idempotent_prompts_and_history(self):
  with tempfile.TemporaryDirectory() as directory:
   provider=OfflineVisibilityProvider({request().prompt.text:("Veloura",())});app=AIVisibilityComposition(AIVisibilitySettings(Path(directory)/"v.db"),[provider]).build();a=await app.add_prompt(request().prompt.text);b=await app.add_prompt(request().prompt.text);self.assertEqual(a.prompt_id,b.prompt_id);report=await app.run((request(),),1);self.assertEqual(len(report.run.observations),1);self.assertEqual(len(await app.history()),1);await app.aclose()
 async def test_prompt_generation_and_category_bounded(self):
  self.assertLessEqual(len(AIVisibilityService.generated_prompts("best lingerie brands india",99)),3);self.assertEqual(AIVisibilityService.category("how to measure bra size"),PromptCategory.QUESTION_AEO)
 async def test_dashboard_no_calls_on_rerender_and_preview(self):
  provider=OfflineVisibilityProvider({request().prompt.text:("Veloura",())});service=AIVisibilityService();rid=uuid4();obs=await service.observe(rid,request(),provider);report=service.report(AIVisibilityRun(run_id=rid,brand_name="Veloura Intimate",target_domain="velouraintimate.com",providers=(provider.capability.provider,),prompt_count=1,repetitions=1,observations=(obs,)))
  class Workflow:
   calls=0
   async def providers(self):return [provider.capability]
   async def prompts(self):return [request().prompt]
   async def candidates(self):return []
   async def add_prompt(self,text):return request(text)
   async def run(self,requests,repetitions,providers):self.calls+=1;return report
   async def history(self):return []
  w=Workflow();view=AppTest.from_function(render,args=(w,)).run(timeout=30);self.assertFalse(view.exception);self.assertEqual(w.calls,0);self.assertIn("Total API calls: 0",view.caption[-1].value)
 async def test_data_honesty(self):
  provider=OfflineVisibilityProvider({request().prompt.text:("Veloura",())});o=await AIVisibilityService().observe(uuid4(),request(),provider);payload=AIVisibilityService().report(AIVisibilityRun(brand_name="Veloura Intimate",target_domain="velouraintimate.com",providers=(provider.capability.provider,),prompt_count=1,observations=(o,))).model_dump_json().lower()
  for claim in ("chatgpt ranking","gemini ranking","ai market share","guaranteed citation","universal ai visibility"):self.assertNotIn(claim,payload)
