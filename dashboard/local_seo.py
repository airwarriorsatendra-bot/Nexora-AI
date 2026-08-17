"""Streamlit Local SEO audit page."""
from __future__ import annotations
import asyncio
import streamlit as st
from dashboard.local_seo_workflow import LocalSEODashboardWorkflow,issues_to_dataframe
from src.local_seo.domain import LocalBusiness
from src.shared.value_objects.location import Location
def run(c):
 try:asyncio.get_running_loop()
 except RuntimeError:return asyncio.run(c)
 raise RuntimeError("Local audit cannot run inside an active event loop.")
def render_local_seo(workflow=None):
 st.session_state.setdefault("local_seo_response",None);workflow=workflow or LocalSEODashboardWorkflow();st.subheader("Local SEO audit");st.caption("Audits supplied business data and website HTML. GBP, reviews, citations, and rank data remain unavailable unless imported.")
 with st.form("local-seo",border=True):
  name=st.text_input("Business name",key="local-name");website=st.text_input("Website URL",key="local-url");phone=st.text_input("Phone",key="local-phone");address=st.text_input("Address",key="local-address");city=st.text_input("City",key="local-city");state=st.text_input("State",key="local-state");category=st.text_input("Primary category",key="local-category");submit=st.form_submit_button("Run local audit",type="primary")
 if submit:
  try:st.session_state.local_seo_response=run(workflow.execute(LocalBusiness(name=name,website=website,phone=phone,location=Location(address=address,city=city,state=state),primary_category=category)))
  except Exception as exc:st.error(str(exc))
 response=st.session_state.local_seo_response
 if response and response.audit:
  audit=response.audit
  with st.container(horizontal=True):st.metric("Local score",f"{audit.overall_score:.0f}",border=True);st.metric("Issues",len(audit.issues),border=True);st.metric("Citation data",audit.signals["citation_consistency"],border=True)
  frame=issues_to_dataframe(audit);st.dataframe(frame,hide_index=True,key="local-issues");st.download_button("Export findings CSV",frame.to_csv(index=False),"nexora_local_seo.csv","text/csv")
 elif response:st.error(response.message)
