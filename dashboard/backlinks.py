"""Premium evidence-scoped Backlink Intelligence 2.0 workspace."""
from __future__ import annotations
import asyncio
from typing import Any
import pandas as pd
import streamlit as st
from dashboard.backlinks_workflow import BacklinksDashboardWorkflow,_frame,backlink_report

def _run(coro:Any)->Any:return asyncio.run(coro)
def _state():
 for key,value in (("backlink_target_domain",""),("backlink_authority_preview",None),("backlink_notice","")):st.session_state.setdefault(key,value)

def render_backlinks(workflow:BacklinksDashboardWorkflow|None=None)->None:
 _state();workflow=workflow or BacklinksDashboardWorkflow();st.subheader("Backlink Intelligence 2.0");st.caption("Provider-observed and Nexora-observed evidence. Not a complete internet backlink index.")
 with st.container(border=True):
  target=st.text_input("Workspace target domain",value=st.session_state.backlink_target_domain,placeholder="example.com");st.session_state.backlink_target_domain=target
 try:snapshot=_run(workflow.snapshot(target))
 except Exception:snapshot={"backlinks":[],"opportunities":[],"authority":[],"prospects":[],"prospect_history":[],"referring_domains":[],"intersect":[],"competitor_gaps":[],"anchors":[],"reclamation":[],"moz_configured":False};st.error("Persisted backlink intelligence could not be loaded.")
 links=snapshot["backlinks"];authority=snapshot["authority"];prospects=snapshot["prospects"];latest=authority[0] if authority else None
 with st.container(horizontal=True):
  st.metric("Observed Backlinks",len(links),border=True);st.metric("Observed Referring Domains",len(snapshot["referring_domains"]),border=True);st.metric("Moz DA",latest.domain_authority if latest and latest.domain_authority is not None else "N/A",border=True);st.metric("Moz PA",latest.page_authority if latest and latest.page_authority is not None else "N/A",border=True);st.metric("High-Priority Prospects",sum(x.priority.value in {"high","critical"} for x in prospects),border=True)
 tabs=st.tabs(["Overview","Backlink Profile","Referring Domains","Authority Intelligence","Competitor Gaps","Link Intersect","Prospects","New / Lost","Broken / Reclamation","History"])
 with tabs[0]:
  st.write("Authority, relevance, risk, and opportunity remain separate evidence dimensions.");st.dataframe(_frame(snapshot["opportunities"]),hide_index=True,width="stretch") if snapshot["opportunities"] else st.info("No persisted backlink opportunities.")
 with tabs[1]:st.dataframe(_frame(links),hide_index=True,width="stretch") if links else st.info("No observed backlinks for this workspace.")
 with tabs[2]:st.dataframe(_frame(snapshot["referring_domains"]),hide_index=True,width="stretch") if snapshot["referring_domains"] else st.info("No observed referring domains.")
 with tabs[3]:
  st.caption("Moz enrichment is explicit, cached for the configured freshness window, and never runs on rerender.")
  with st.form("moz-authority-enrichment",border=True):
   values=st.text_area("URLs or domains to enrich",placeholder="One target per line");scope=st.selectbox("Moz scope",("url","domain","subdomain","subfolder"));force=st.checkbox("Force refresh cached observations");preview=st.form_submit_button("Preview requests");enrich=st.form_submit_button("Enrich with Moz",type="primary",disabled=not snapshot["moz_configured"])
  targets=[x.strip() for x in values.splitlines() if x.strip()]
  if preview:
   try:st.session_state.backlink_authority_preview=_run(workflow.preview_authority(targets,scope,force))
   except Exception:st.error("Authority request preview could not be created.")
  if st.session_state.backlink_authority_preview:st.json(st.session_state.backlink_authority_preview.model_dump(mode="json"))
  if enrich:
   try:_run(workflow.enrich_authority(targets,scope,force));st.success("Moz authority observations persisted. Refresh the page to view them.")
   except Exception:st.error("Moz authority enrichment failed. No credential or provider details are displayed.")
  if not snapshot["moz_configured"]:st.info("MOZ_API_TOKEN missing. Persisted authority history remains available.")
  st.dataframe(_frame(authority),hide_index=True,width="stretch") if authority else st.info("No authority observations are persisted.")
 with tabs[4]:
  st.caption("Observed competitor gaps only; not observed does not mean nonexistent.")
  st.dataframe(_frame(snapshot["competitor_gaps"]),hide_index=True,width="stretch") if snapshot["competitor_gaps"] else st.info("No compatible competitor-gap evidence.")
 with tabs[5]:st.dataframe(_frame(snapshot["intersect"]),hide_index=True,width="stretch") if snapshot["intersect"] else st.info("No compatible link-intersect evidence.")
 with tabs[6]:
  st.dataframe(_frame(prospects),hide_index=True,width="stretch") if prospects else st.info("No persisted prospects. Discovery never triggers Moz automatically.")
  if prospects:
   selected=st.selectbox("Prospect detail",prospects,format_func=lambda item:f"{item.domain} · {item.priority.value} · {item.score}")
   with st.container(border=True):
    st.write("Evidence summary");st.write(list(selected.reasons) or ["No additional evidence summary persisted."])
    st.write({"authority_provider":"MOZ" if selected.authority_observation_id else "NOT_REQUESTED","moz_da":selected.domain_authority,"moz_pa":selected.page_authority,"moz_spam_score":selected.spam_score,"target_page":str(selected.target_page or ""),"outreach_handoff_ready":bool(selected.target_page and selected.reasons)})
 with tabs[7]:st.dataframe(_frame([x for x in links if x.status.value in {"verified","lost"}]),hide_index=True,width="stretch") if links else st.info("No new/lost evidence.")
 with tabs[8]:st.dataframe(_frame(snapshot["reclamation"]),hide_index=True,width="stretch") if snapshot["reclamation"] else st.info("No evidence-backed reclamation actions.")
 with tabs[9]:
  st.caption("Authority and prospect observations are provider-compatible histories; unlike providers are not treated as equivalent.")
  st.dataframe(_frame(authority),hide_index=True,width="stretch") if authority else st.info("No authority history.")
  if snapshot["prospect_history"]:st.dataframe(_frame(snapshot["prospect_history"]),hide_index=True,width="stretch")
 exports=(("Authority CSV",authority,"authority.csv"),("Backlinks CSV",links,"backlinks.csv"),("Referring Domains CSV",snapshot["referring_domains"],"referring_domains.csv"),("Competitor Gap CSV",snapshot["competitor_gaps"],"competitor_gaps.csv"),("Link Intersect CSV",snapshot["intersect"],"link_intersect.csv"),("Prospects CSV",prospects,"prospects.csv"),("New Lost CSV",[x for x in links if x.status.value in {"verified","lost"}],"new_lost.csv"),("Reclamation CSV",snapshot["reclamation"],"reclamation.csv"))
 with st.container(horizontal=True):
  for label,items,name in exports:st.download_button(label,_frame(items).to_csv(index=False),name,"text/csv")
  st.download_button("Markdown Report",backlink_report(snapshot),"backlink_intelligence.md","text/markdown")
