"""Rank Tracking UI; provider calls occur only on explicit Check ranks."""
from __future__ import annotations
import asyncio
import altair as alt
import pandas as pd
import streamlit as st
from dashboard.rank_tracking_workflow import RankTrackingDashboardWorkflow
def _run_async(coro):return asyncio.run(coro)
def _current_frame(rows):
 columns=["Keyword","Target","Tracked Position","Previous","Change","Movement","GSC Avg Position","Clicks","Impressions","Last Checked","Keyword ID"]
 return pd.DataFrame([{"Keyword":k.keyword,"Target":k.target_url or k.target_domain,"Tracked Position":c.position_label,"Previous":ch.previous_position if ch.previous_position is not None else "NOT AVAILABLE","Change":ch.change_type.value,"Movement":ch.movement,"GSC Avg Position":float(k.gsc_average_position) if k.gsc_average_position is not None else None,"Clicks":k.gsc_clicks,"Impressions":k.gsc_impressions,"Last Checked":c.checked_at,"Keyword ID":str(k.keyword_id)} for k,c,ch in rows if k],columns=columns)
def render_rank_tracking(workflow=None):
 workflow=workflow or RankTrackingDashboardWorkflow();st.caption("Point-in-time observed Google SERP results. Tracked position is separate from GSC average position.")
 with st.form("rank-add",border=True):
  keyword=st.text_input("Add keyword");target=st.text_input("Target domain/URL");country=st.selectbox("Country",("US","IN","GB","AU"));device=st.selectbox("Device",("desktop","mobile"));add=st.form_submit_button("Add to Rank Tracker")
 if add:
  try:
   is_url="://" in target;domain=(target.split("//",1)[-1].split("/",1)[0]);_run_async(workflow.add(keyword,domain,target if is_url else "",country,device));st.success("Keyword added.")
  except Exception:st.error("Keyword could not be added.")
 configured=workflow.configured()
 if not configured:st.info("Live rank checks are not configured. Set SERPER_API_KEY; stored and offline data remain available.")
 depth=st.selectbox("Search depth",(10,20,50),index=1,key="rank-depth")
 if st.button("Check Ranks",type="primary",disabled=not configured,key="rank-check"):
  try:_run_async(workflow.check(depth));st.success("Explicit rank check completed.")
  except Exception:st.error("Rank check failed. Provider details and credentials are not displayed.")
 try:data=_run_async(workflow.snapshot())
 except Exception:st.error("Rank tracking data could not be loaded.");return
 keywords,rows,competitors=data["keywords"],data["rows"],data["competitors"];frame=_current_frame(rows)
 with st.container(horizontal=True):
  st.metric("Tracked Keywords",len(keywords),border=True);st.metric("Top 3",sum(c.target_position is not None and c.target_position<=3 for _,c,_ in rows),border=True);st.metric("Top 10",sum(c.target_position is not None and c.target_position<=10 for _,c,_ in rows),border=True);st.metric("Improved",sum(ch.change_type.value=="IMPROVED" for _,_,ch in rows),border=True);st.metric("Declined",sum(ch.change_type.value=="DECLINED" for _,_,ch in rows),border=True)
 tabs=st.tabs(["Current Rankings","Rank History","SERP Snapshot","Competitors","Winners / Losers"])
 with tabs[0]:st.dataframe(frame.drop(columns=["Keyword ID"],errors="ignore"),hide_index=True,width="stretch");st.download_button("Export current rankings CSV",frame.to_csv(index=False),"nexora_current_rankings.csv","text/csv")
 selected=st.selectbox("Tracked keyword",keywords,format_func=lambda k:k.keyword,key="rank-selected") if keywords else None
 history=_run_async(workflow.history(selected)) if selected else []
 history_frame=pd.DataFrame([{"Checked At":c.checked_at,"Observed Position":c.target_position,"State":c.position_label,"Depth":c.depth,"Provider":c.provider} for c in history])
 with tabs[1]:
  if history_frame.empty:st.info("No observed rank history.")
  else:
   chart_data=history_frame.dropna(subset=["Observed Position"])
   chart=alt.Chart(chart_data).mark_line(point=True).encode(x=alt.X("Checked At:T",title="Checked at"),y=alt.Y("Observed Position:Q",title="Observed position",scale=alt.Scale(reverse=True)),tooltip=["Checked At","Observed Position","State"])
   st.altair_chart(chart,use_container_width=True);st.caption("Position 1 is shown at the top; observed checks only.");st.download_button("Export rank history CSV",history_frame.to_csv(index=False),"nexora_rank_history.csv","text/csv")
 latest=history[-1] if history else None;serp=pd.DataFrame([r.model_dump(mode="json") for r in latest.results]) if latest else pd.DataFrame()
 with tabs[2]:st.dataframe(serp,hide_index=True,width="stretch") if not serp.empty else st.info("No captured SERP snapshot.");st.download_button("Export SERP snapshot CSV",serp.to_csv(index=False),"nexora_serp_snapshot.csv","text/csv",disabled=serp.empty)
 comp=pd.DataFrame([c.model_dump(mode="json") for c in competitors])
 with tabs[3]:st.dataframe(comp,hide_index=True,width="stretch") if not comp.empty else st.info("No competitor observations.");st.download_button("Export competitors CSV",comp.to_csv(index=False),"nexora_serp_competitors.csv","text/csv",disabled=comp.empty)
 with tabs[4]:st.dataframe(frame[frame["Change"].isin(["IMPROVED","DECLINED","NEWLY_RANKING","LOST"])].drop(columns=["Keyword ID"],errors="ignore"),hide_index=True,width="stretch")
 tracked=pd.DataFrame([k.model_dump(mode="json") for k in keywords]);st.download_button("Export tracked keywords CSV",tracked.to_csv(index=False),"nexora_tracked_keywords.csv","text/csv")
