from __future__ import annotations
import asyncio
import pandas as pd
import streamlit as st
from dashboard.content_intelligence_workflow import ContentIntelligenceDashboardWorkflow
from src.content_intelligence.service import ContentIntelligenceService
def run(c):return asyncio.run(c)
def render_content_intelligence(workflow=None):
 workflow=workflow or ContentIntelligenceDashboardWorkflow();st.subheader("Content Intelligence & SEO Content Briefs");st.caption("Deterministic briefs from persisted GSC, GA4, tracked SERPs, competitor gaps, and host-scoped crawl evidence.");st.session_state.setdefault("content_brief",None)
 try:options=run(workflow.targets())
 except Exception:options=[]
 if not options:st.info("No persisted competitor-gap keyword evidence is available for a content brief.");return
 labels={f"{keyword} — {target}":(target,keyword,page) for target,keyword,page in options};choice=st.selectbox("Target keyword",labels);target,keyword,page=labels[choice];st.text_input("Target page",value=page or "NOT AVAILABLE",disabled=True);st.selectbox("Brief type",("Deterministic evidence brief",),disabled=True)
 if st.button("Generate brief",type="primary",key="content-brief-generate"):
  try:st.session_state.content_brief=run(workflow.generate(target,keyword))
  except Exception:st.error("The persisted evidence brief could not be generated.")
 b=st.session_state.content_brief
 if b is None:st.info("Generate a brief explicitly. No API or AI call occurs on rerender.");return
 with st.container(horizontal=True):
  st.metric("Priority",b.priority.value,border=True);st.metric("Opportunity score",b.score.total,border=True);st.metric("GSC impressions",b.gsc_impressions if b.gsc_impressions is not None else "NOT AVAILABLE",border=True);st.metric("Tracked rank",b.tracked_position if b.tracked_position is not None else "NOT FOUND",border=True);st.metric("Competitors ahead",b.competitors_ahead,border=True);st.metric("Technical issues",len(b.technical_issues),border=True)
 st.subheader("Overview");st.write(f"**Mode:** {b.mode.value}");st.write(f"**Primary query:** {b.primary_query}");st.caption(b.primary_query_reason)
 st.subheader("Search intent observation");st.write(b.intent.value);[st.caption(x) for x in b.intent_evidence]
 current,queries,serp=st.tabs(["Current page","Query set","Observed SERP competitors"])
 with current:st.dataframe(pd.DataFrame([{"Target URL":b.target_url or "NOT AVAILABLE","Title":b.current_title or "NOT AVAILABLE","Meta":b.current_meta or "NOT AVAILABLE","H1":b.current_h1 or "NOT AVAILABLE","Depth":b.crawl_depth,"Inlinks":b.inlinks,"Technical issues":"; ".join(b.technical_issues)}]),hide_index=True,width="stretch")
 with queries:st.dataframe(pd.DataFrame([q.model_dump(mode="json") for q in b.supporting_queries]),hide_index=True,width="stretch")
 with serp:st.dataframe(pd.DataFrame([x.model_dump(mode="json") for x in b.serp_competitors]),hide_index=True,width="stretch")
 for title,values in (("Content gap observations",b.content_gap_observations),("Title guidance",b.title_guidance),("Meta guidance",b.meta_guidance),("Suggested heading outline",(f"H1: {b.suggested_h1}",)+b.h2_sections),("AEO opportunities",b.aeo_opportunities),("GEO readiness",b.geo_readiness),("Question opportunities",b.question_opportunities),("Direct answer suggestions",b.direct_answer_suggestions),("FAQ opportunities",b.faq_opportunities),("Entity / source support",b.entity_source_support),("Technical preconditions",b.technical_preconditions),("Action plan",b.actions),("Provenance and limitations",tuple(e.observation for e in b.evidence)+b.limitations)):
  st.subheader(title)
  if values:
   for value in values:st.write(f"- {value}")
  else:st.caption("NOT AVAILABLE")
 markdown=ContentIntelligenceService.markdown(b);st.download_button("Export Markdown content brief",markdown,"nexora_content_brief.md","text/markdown");st.download_button("Export structured JSON",b.model_dump_json(indent=2),"nexora_content_brief.json","application/json")
