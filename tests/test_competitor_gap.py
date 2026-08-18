from __future__ import annotations
import unittest
from datetime import UTC,datetime,timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4
from streamlit.testing.v1 import AppTest
from src.competitor_gap.domain import ContentGapType,KeywordGapType
from src.competitor_gap.service import CompetitorGapService
from src.rank_tracking.domain import RankCheck,SERPResult,TrackedKeyword,TrackingContext
def serp(pos,domain,path="/"):return SERPResult(position=pos,title=domain,url=f"https://{domain}{path}",domain=domain)
def render(workflow):
 from dashboard.competitor_gap import render_competitor_gap
 render_competitor_gap(workflow)
class CompetitorGapTests(unittest.TestCase):
 def setUp(self):
  self.service=CompetitorGapService();self.kid=uuid4();self.keyword=TrackedKeyword(keyword="best lingerie brand india",keyword_id=self.kid,target_domain="target.com",target_url="https://target.com/lingerie")
  self.check=RankCheck(keyword_id=self.kid,keyword=self.keyword.keyword,context=self.keyword.context,depth=10,provider="offline",target_position=3,results=(serp(1,"competitor-a.com"),serp(2,"competitor-b.com"),serp(3,"target.com"),serp(4,"competitor-a.com","/duplicate")))
 def report(self,check=None,keyword=None,**kwargs):return self.service.analyze("target.com",[keyword or self.keyword],[check or self.check],**kwargs)
 def test_competitor_discovery_excludes_target_deduplicates_and_aggregates(self):
  report=self.report();a=next(c for c in report.competitors if c.domain=="competitor-a.com");self.assertEqual(a.keywords_observed,1);self.assertEqual(a.serp_appearances,1);self.assertEqual(a.top_3_appearances,1);self.assertEqual(a.best_observed_position,1);self.assertNotIn("target.com",[c.domain for c in report.competitors])
 def test_gap_types_positions_and_multiple_competitors(self):
  gap=self.report().keyword_gaps[0];self.assertEqual(gap.gap_type,KeywordGapType.COMPETITOR_AHEAD);self.assertIn("SHARED_TOP_10",gap.flags);self.assertEqual(gap.competitors_ahead,2)
  missing=self.check.model_copy(update={"target_position":None,"results":(serp(1,"competitor-a.com"),serp(2,"competitor-b.com"))});gap=self.report(missing).keyword_gaps[0];self.assertEqual(gap.gap_type,KeywordGapType.COMPETITOR_TOP_3_TARGET_OUTSIDE_TOP_10);self.assertEqual(gap.target_position_label,"NOT_FOUND_IN_TOP_10")
  ahead=self.check.model_copy(update={"target_position":1,"results":(serp(1,"target.com"),serp(3,"competitor-a.com"))});self.assertEqual(self.report(ahead).keyword_gaps[0].gap_type,KeywordGapType.SHARED_TOP_10)
 def test_gsc_page_content_score_and_source_separation(self):
  crawl=SimpleNamespace(inlink_count=2,depth=3,issues=("thin",));gsc={self.keyword.keyword:(5000,150,Decimal("7.5"),Decimal("0.03"))};ga4={self.keyword.target_url:(Decimal(200),Decimal("0.65"))}
  gap=self.report(gsc_queries=gsc,ga4_pages=ga4,crawl_pages={self.keyword.target_url:crawl}).keyword_gaps[0];self.assertEqual(gap.content_gap,ContentGapType.EXISTING_PAGE_OPTIMIZATION);self.assertEqual(gap.gsc_average_position,Decimal("7.5"));self.assertEqual(gap.target_position,3);self.assertLessEqual(gap.score.total,100);self.assertTrue(gap.evidence)
  no_page=self.keyword.model_copy(update={"target_url":None});missing=self.check.model_copy(update={"target_position":None});gap=self.report(missing,no_page).keyword_gaps[0];self.assertEqual(gap.content_gap,ContentGapType.POSSIBLE_NEW_CONTENT_GAP);self.assertIn("validate search intent",gap.recommended_action)
 def test_history_trends_require_compatible_context(self):
  old=self.check.model_copy(update={"checked_at":datetime.now(UTC)-timedelta(days=1),"results":(serp(8,"competitor-a.com"),serp(3,"target.com"))});new=self.check.model_copy(update={"results":(serp(2,"competitor-a.com"),serp(3,"target.com"))});report=self.service.analyze("target.com",[self.keyword],[new],{self.kid:(old,new)});self.assertEqual(report.trends[0].trend,"IMPROVING")
  other=new.model_copy(update={"context":TrackingContext(country="IN")});report=self.service.analyze("target.com",[self.keyword],[other],{self.kid:(old,other)});self.assertFalse(report.trends)
 def test_data_honesty_and_dashboard_exports_no_provider_calls(self):
  report=self.report();payload=report.model_dump_json().lower()
  for forbidden in ("search volume","keyword difficulty","competitor traffic","domain authority","guaranteed ranking improvement"):self.assertNotIn(forbidden,payload)
  self.assertIn("not organic market share",payload)
  class Workflow:
   calls=0
   async def targets(self):return ["target.com"]
   async def load(self,target):self.calls+=1;return report
  workflow=Workflow();view=AppTest.from_function(render,args=(workflow,));view.run(timeout=30);self.assertFalse(view.exception);self.assertEqual(workflow.calls,1);self.assertEqual(len(view.metric),5);self.assertGreaterEqual(len(view.download_button),5);self.assertTrue(view.dataframe)
