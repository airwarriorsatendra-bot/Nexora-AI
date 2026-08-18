"""Offline-first Outreach Automation and CRM Intelligence workspace."""
from __future__ import annotations
import asyncio
from typing import Any
import streamlit as st
from dashboard.outreach_workflow import OutreachDashboardWorkflow,outreach_frame,outreach_report
from src.core.enums import CampaignObjective

def _run(coro):return asyncio.run(coro)

def render_outreach(_st:Any=None,_dataframe:Any=None,workflow:OutreachDashboardWorkflow|None=None)->None:
 del _st,_dataframe;workflow=workflow or OutreachDashboardWorkflow()
 for key in ("outreach_campaign","outreach_candidate","outreach_message"):st.session_state.setdefault(key,None)
 st.subheader("Outreach Automation · offline");st.caption("CRM, campaigns and reviewed dry-runs. Live delivery never occurs on rerender.")
 try:snapshot=_run(workflow.snapshot())
 except Exception:
  class EmptyAnalytics:
   prospects=contacts=sent=failed=bounced=replies=positive_replies=negative_replies=0;reply_rate=positive_reply_rate=bounce_rate=0.0
  snapshot={"prospects":[],"contacts":[],"campaigns":[],"sequences":[],"steps":[],"messages":[],"replies":[],"followups":[],"suppressions":[],"history":[],"analytics":EmptyAnalytics()};st.error("Persisted outreach workspace could not be loaded.")
 a=snapshot["analytics"]
 with st.container(horizontal=True):
  for label,value in (("Prospects",a.prospects),("Contacts found",a.contacts),("Messages sent",a.sent),("Replies",a.replies),("Positive replies",a.positive_replies),("Follow-ups due",len(snapshot["followups"])),("Suppressed",len(snapshot["suppressions"]))):st.metric(label,value,border=True)
 tabs=st.tabs(["Overview","Prospects","Contacts","Campaigns","Sequences","Messages","Replies","Follow-ups","Suppression","Analytics","History"])
 with tabs[0]:st.caption("Exact persisted funnel counts. Open rates and guaranteed backlink gains are not claimed.")
 for tab,key in zip((tabs[1],tabs[2],tabs[3],tabs[4],tabs[5],tabs[6],tabs[7],tabs[8],tabs[10]),("prospects","contacts","campaigns","steps","messages","replies","followups","suppressions","history")):
  with tab:st.dataframe(outreach_frame(snapshot[key]),hide_index=True,width="stretch") if snapshot[key] else st.info("No persisted records.")
 with tabs[9]:st.write({"reply_rate":a.reply_rate,"positive_reply_rate":a.positive_reply_rate,"bounce_rate":a.bounce_rate,"failed":a.failed})
 with st.form("outreach-campaign",border=True):
  name=st.text_input("Campaign name");description=st.text_input("Description");objective=st.selectbox("Objective",list(CampaignObjective),format_func=lambda x:x.value.replace("_"," "));create=st.form_submit_button("Create draft campaign",type="primary")
 if create:
  try:st.session_state.outreach_campaign=_run(workflow.create_campaign(name,description,objective));st.success("Draft campaign created.")
  except Exception as exc:st.error(str(exc))
 with st.form("outreach-candidate",border=True):
  url=st.text_input("Website URL",placeholder="https://publisher.example");email=st.text_input("Recipient email");contact=st.text_input("Contact name");add=st.form_submit_button("Add verified candidate")
 if add:
  try:st.session_state.outreach_candidate=_run(workflow.add_candidate(url,email,contact));st.success("Candidate added.")
  except Exception as exc:st.error(str(exc))
 campaign=st.session_state.outreach_campaign;candidate=st.session_state.outreach_candidate
 if campaign and candidate:
  with st.form("outreach-preview",border=True):
   subject=st.text_input("Subject template","Hello {{first_name}}");body=st.text_area("Body template","Hello {{first_name}},\n\nI am reaching out about {{domain}}.");preview=st.form_submit_button("Prepare exact message preview")
  if preview:
   try:st.session_state.outreach_message=_run(workflow.prepare(campaign.campaign_id,candidate.candidate_id,subject,body))
   except Exception as exc:st.error(str(exc))
 message=st.session_state.outreach_message
 if message and candidate:
  with st.container(border=True):st.write({"recipient":str(candidate.email),"subject":message.subject,"campaign":str(message.campaign_id),"sequence_step":message.sequence_step,"provider":"fake","expected_send_count":1});st.write(message.body)
  confirm=st.checkbox("I reviewed the exact recipient, subject and rendered body")
  if st.button("Record delivery dry-run",disabled=not confirm):
   try:_run(workflow.send(message.message_id,True));st.success("Dry-run recorded. No email transmitted.")
   except Exception as exc:st.error(str(exc))
 with st.container(horizontal=True):
  for label,key in (("Prospects CSV","prospects"),("Contacts CSV","contacts"),("Campaigns CSV","campaigns"),("Messages CSV","messages"),("Replies CSV","replies"),("Suppression CSV","suppressions")):st.download_button(label,outreach_frame(snapshot[key]).to_csv(index=False),f"{key}.csv","text/csv")
  st.download_button("Campaign Analytics CSV",outreach_frame([a]).to_csv(index=False),"campaign_analytics.csv","text/csv")
  st.download_button("Markdown Outreach Report",outreach_report(snapshot),"outreach_report.md","text/markdown")
