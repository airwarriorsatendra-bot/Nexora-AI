"""Persisted-only Competitor & Keyword Gap Intelligence dashboard."""
from __future__ import annotations
import asyncio
import pandas as pd
import streamlit as st
from dashboard.competitor_gap_workflow import CompetitorGapDashboardWorkflow
def run(coro):return asyncio.run(coro)
def render_competitor_gap(workflow=None):
 workflow=workflow or CompetitorGapDashboardWorkflow();st.subheader("Competitor & Keyword Gap Intelligence");st.caption("Evidence from tracked SERPs, GSC, host-scoped crawl, and URL-matched GA4. No API calls run here.")
 try:targets=run(workflow.targets())
 except Exception:targets=[]
 if not targets:st.info("No persisted tracked-keyword SERP evidence is available.");return
 target=st.selectbox("Target domain",targets,key="gap-target")
 try:report=run(workflow.load(target))
 except Exception:st.error("Persisted competitor-gap evidence could not be loaded.");return
 domains=[c.domain for c in report.competitors];competitor=st.selectbox("Competitor filter",["All"]+domains);types=st.multiselect("Opportunity type",sorted({g.gap_type.value for g in report.keyword_gaps}),default=sorted({g.gap_type.value for g in report.keyword_gaps}));priorities=st.multiselect("Priority",[p for p in ("CRITICAL","HIGH","MEDIUM","LOW")],default=["CRITICAL","HIGH","MEDIUM","LOW"]);minimum=st.number_input("Minimum GSC impressions",0,value=0);search=st.text_input("Search keywords")
 gaps=[g for g in report.keyword_gaps if g.gap_type.value in types and g.priority.value in priorities and (g.gsc_impressions or 0)>=minimum and (competitor=="All" or g.best_competitor==competitor) and (not search or search.casefold() in g.keyword.casefold())]
 with st.container(horizontal=True):
  st.metric("Competitors observed",len(report.competitors),border=True);st.metric("Keyword gaps",len(report.keyword_gaps),border=True);st.metric("High priority gaps",sum(g.priority.value in {"CRITICAL","HIGH"} for g in report.keyword_gaps),border=True);st.metric("Competitor-ahead keywords",sum("COMPETITOR_AHEAD" in g.flags for g in report.keyword_gaps),border=True);st.metric("Possible content gaps",sum(g.content_gap.value=="POSSIBLE_NEW_CONTENT_GAP" for g in report.keyword_gaps),border=True)
 for note in report.notes:st.info(note)
 overview,keywords,pages,serp_tab,trends,content=st.tabs(["Competitor overview","Keyword gaps","Page gaps","Observed SERP","Winners / losers","Content gaps"])
 competitor_frame=pd.DataFrame([{"Domain":c.domain,"Keywords observed":c.keywords_observed,"SERP appearances":c.serp_appearances,"Top 3":c.top_3_appearances,"Top 10":c.top_10_appearances,"Average observed position":float(c.average_observed_position),"Target overlap":c.target_overlap,"Observed top-10 coverage":float(c.observed_top_10_coverage)} for c in report.competitors])
 gap_frame=pd.DataFrame([{"Priority":g.priority.value,"Keyword":g.keyword,"Gap type":g.gap_type.value,"Target position":g.target_position_label,"Best competitor":g.best_competitor,"Competitor position":g.competitor_position,"Competitors ahead":g.competitors_ahead,"GSC avg position":float(g.gsc_average_position) if g.gsc_average_position is not None else "NOT AVAILABLE","GSC impressions":g.gsc_impressions if g.gsc_impressions is not None else "NOT AVAILABLE","GSC clicks":g.gsc_clicks if g.gsc_clicks is not None else "NOT AVAILABLE","Mapped page":g.mapped_page or "NOT AVAILABLE","Opportunity score":g.score.total,"Content classification":g.content_gap.value,"Recommended action":g.recommended_action} for g in gaps])
 page_frame=pd.DataFrame([p.model_dump(mode="json") for p in report.page_gaps]);trend_frame=pd.DataFrame([t.model_dump(mode="json") for t in report.trends]);action_frame=gap_frame[["Priority","Keyword","Content classification","Recommended action"]] if not gap_frame.empty else gap_frame
 with overview:st.dataframe(competitor_frame,hide_index=True,width="stretch");st.download_button("Export competitor domains CSV",competitor_frame.to_csv(index=False),"nexora_competitor_domains.csv","text/csv")
 with keywords:st.dataframe(gap_frame,hide_index=True,width="stretch");st.download_button("Export keyword gaps CSV",gap_frame.to_csv(index=False),"nexora_keyword_gaps.csv","text/csv")
 with pages:st.dataframe(page_frame,hide_index=True,width="stretch");st.download_button("Export page gaps CSV",page_frame.to_csv(index=False),"nexora_page_gaps.csv","text/csv")
 with serp_tab:
  selected=st.selectbox("Tracked keyword",report.keyword_gaps,format_func=lambda g:g.keyword,key="gap-serp-keyword") if report.keyword_gaps else None;frame=pd.DataFrame([r.model_dump(mode="json") for r in selected.serp]) if selected else pd.DataFrame();st.dataframe(frame,hide_index=True,width="stretch")
 with trends:st.dataframe(trend_frame,hide_index=True,width="stretch");st.download_button("Export competitive trends CSV",trend_frame.to_csv(index=False),"nexora_competitive_trends.csv","text/csv")
 with content:st.dataframe(action_frame,hide_index=True,width="stretch");st.download_button("Export recommended actions CSV",action_frame.to_csv(index=False),"nexora_competitive_actions.csv","text/csv")
