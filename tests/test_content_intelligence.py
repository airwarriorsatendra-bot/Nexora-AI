from __future__ import annotations
import unittest
from decimal import Decimal
from uuid import uuid4
from streamlit.testing.v1 import AppTest
from src.competitor_gap.service import CompetitorGapService
from src.content_intelligence.domain import ContentMode,SearchIntent
from src.content_intelligence.service import ContentIntelligenceService
from src.rank_tracking.domain import RankCheck,SERPResult,TrackedKeyword
from src.site_crawl.domain import CrawledPage,IndexabilitySignal,InternalLink
def result(pos,domain,path="/"):return SERPResult(position=pos,title=domain,url=f"https://{domain}{path}",domain=domain)
def render(workflow):
 from dashboard.content_intelligence import render_content_intelligence
 render_content_intelligence(workflow)
class ContentIntelligenceTests(unittest.TestCase):
 def gap(self,mapped=True,absent=False,query="best lingerie brand india"):
  kid=uuid4();k=TrackedKeyword(keyword=query,keyword_id=kid,target_domain="example.com",target_url="https://example.com/best-lingerie" if mapped else None);c=RankCheck(keyword_id=kid,keyword=query,context=k.context,depth=10,provider="offline",target_position=None if absent else 5,results=(result(1,"competitor-a.com","/shop"),result(2,"competitor-b.com","/guide"))+(tuple() if absent else (result(5,"example.com","/best-lingerie"),)));gsc={query:(5000,150,Decimal("7.5"),Decimal("0.03"))};return CompetitorGapService().analyze("example.com",[k],[c],gsc_queries=gsc).keyword_gaps[0]
 def test_existing_page_mode_score_and_evidence(self):
  page=CrawledPage(url="https://example.com/best-lingerie",normalized_url="https://example.com/best-lingerie",status_code=200,content_type="text/html",title="Best lingerie",meta_description="",h1s=("Best lingerie",),depth=3,inlink_count=2,indexability=IndexabilitySignal.INDEXABLE,issues=("missing_meta_description",));b=ContentIntelligenceService().generate(self.gap(),page=page);self.assertEqual(b.mode,ContentMode.OPTIMIZE_EXISTING_PAGE);self.assertLessEqual(b.score.total,100);self.assertIn("missing_meta_description",b.technical_issues);self.assertTrue(any("snippet" in x.lower() or "describe" in x.lower() for x in b.meta_guidance))
 def test_possible_new_content_and_intent_are_cautious(self):
  b=ContentIntelligenceService().generate(self.gap(False,True,"bridal lingerie guide"));self.assertEqual(b.mode,ContentMode.POSSIBLE_NEW_CONTENT);self.assertIn(b.intent,(SearchIntent.INFORMATIONAL,SearchIntent.MIXED));self.assertTrue(any("validate" in x.lower() for x in b.actions));self.assertNotIn("mandatory",b.model_dump_json().lower())
 def test_technical_preconditions_and_internal_links(self):
  page=CrawledPage(url="https://example.com/best-lingerie",normalized_url="https://example.com/best-lingerie",status_code=200,content_type="text/html",title="",h1s=(),robots="noindex",indexability=IndexabilitySignal.NON_INDEXABLE,depth=3,inlink_count=1,issues=("noindex_signal","missing_h1"));link=InternalLink(source_url="https://example.com/category",target_url=page.normalized_url,anchor_text="lingerie",depth=1);b=ContentIntelligenceService().generate(self.gap(),page=page,links=(link,));self.assertTrue(b.technical_preconditions);self.assertTrue(b.internal_links);self.assertEqual(b.internal_links[0].source_page,"https://example.com/category")
 def test_supporting_queries_bounded_exports_and_honesty(self):
  primary=self.gap();others=tuple(self.gap(query=f"best lingerie guide {i}") for i in range(20));b=ContentIntelligenceService().generate(primary,(primary,)+others);self.assertLessEqual(len(b.supporting_queries),10);md=ContentIntelligenceService.markdown(b);self.assertIn("SEO Content Brief",md)
  payload=(b.model_dump_json()+md).lower()
  for claim in ("domain authority","guaranteed ranking improvement"):self.assertNotIn(claim,payload)
  self.assertIn("search volume, keyword difficulty, competitor traffic, authority metrics, and guaranteed outcomes are not available",payload)
 def test_question_brief_includes_deterministic_aeo_geo_sections(self):
  b=ContentIntelligenceService().generate(self.gap(query="how to choose lingerie"),page=CrawledPage(url="https://example.com/best-lingerie",normalized_url="https://example.com/best-lingerie",status_code=200,content_type="text/html",title="Guide",h1s=("Guide",),depth=1,indexability=IndexabilitySignal.INDEXABLE));md=ContentIntelligenceService.markdown(b);self.assertTrue(b.aeo_opportunities);self.assertTrue(b.geo_readiness);self.assertTrue(b.direct_answer_suggestions);self.assertIn("## AEO opportunities",md);self.assertIn("## GEO readiness",md);self.assertIn("not ranking or AI-citation guarantees",md)
 def test_dashboard_explicit_generation_and_exports(self):
  brief=ContentIntelligenceService().generate(self.gap())
  class Workflow:
   calls=0
   async def targets(self):return [("example.com",brief.primary_query,brief.target_url)]
   async def generate(self,target,keyword):self.calls+=1;return brief
  w=Workflow();view=AppTest.from_function(render,args=(w,));view.run(timeout=30);self.assertFalse(view.exception);self.assertEqual(w.calls,0);next(b for b in view.button if b.label=="Generate brief").click();view.run(timeout=30);self.assertFalse(view.exception);self.assertEqual(w.calls,1);self.assertEqual(len(view.metric),6);self.assertEqual(len(view.download_button),2)
