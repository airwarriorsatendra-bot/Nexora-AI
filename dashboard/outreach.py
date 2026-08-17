"""Safe Streamlit presentation for source-layer Outreach Automation."""

from __future__ import annotations

import asyncio
from typing import Any

import streamlit as st

from dashboard.outreach_workflow import OutreachDashboardWorkflow
from src.core.enums import CampaignObjective, CampaignStatus


def _run_async(coro: Any) -> Any:
    try: asyncio.get_running_loop()
    except RuntimeError: return asyncio.run(coro)
    raise RuntimeError("Outreach actions cannot start in an active event loop.")


def render_outreach(_st: Any = None, _dataframe: Any = None, workflow: OutreachDashboardWorkflow | None = None) -> None:
    """Preserves the legacy call signature while exposing only explicit safe actions."""
    del _st, _dataframe
    workflow=workflow or OutreachDashboardWorkflow()
    st.session_state.setdefault("outreach_campaign", None); st.session_state.setdefault("outreach_candidate", None); st.session_state.setdefault("outreach_message", None)
    st.subheader("Outreach automation")
    st.caption("Messages are prepared and validated first. Delivery is dry-run by default and never starts on page render.")
    with st.form("outreach-campaign",border=True):
        name=st.text_input("Campaign name",key="outreach-name"); description=st.text_input("Description",key="outreach-description")
        objective=st.selectbox("Objective",list(CampaignObjective),format_func=lambda x:x.value.replace("_"," "),key="outreach-objective")
        create=st.form_submit_button("Create draft campaign",type="primary")
    if create:
        try: st.session_state.outreach_campaign=_run_async(workflow.create_campaign(name,description,objective)); st.success("Draft campaign created.")
        except Exception as exc: st.error(str(exc))
    campaign=st.session_state.outreach_campaign
    with st.form("outreach-candidate",border=True):
        url=st.text_input("Website URL",placeholder="https://publisher.example",key="outreach-url"); email=st.text_input("Recipient email",key="outreach-email"); contact=st.text_input("Contact name",key="outreach-contact")
        add=st.form_submit_button("Add qualified candidate")
    if add:
        try: st.session_state.outreach_candidate=_run_async(workflow.add_candidate(url,email,contact)); st.success("Candidate added.")
        except Exception as exc: st.error(str(exc))
    candidate=st.session_state.outreach_candidate
    if campaign is not None and candidate is not None:
        with st.form("outreach-preview",border=True):
            subject=st.text_input("Subject template","Hello {{contact_name}}",key="outreach-subject")
            body=st.text_area("Body template","Hello {{contact_name}},\n\nI enjoyed {{domain}} and would welcome a relevant collaboration conversation.",key="outreach-body")
            preview=st.form_submit_button("Prepare message preview")
        if preview:
            try: st.session_state.outreach_message=_run_async(workflow.prepare(campaign.campaign_id,candidate.candidate_id,subject,body)); st.success("Message prepared; it has not been sent.")
            except Exception as exc: st.error(str(exc))
    message=st.session_state.outreach_message
    if message is not None:
        st.json(message.model_dump(mode="json"))
        if st.button("Run delivery dry-run",key="outreach-dry-run"):
            try: st.session_state.outreach_message=_run_async(workflow.send(message.message_id,True)); st.success("Dry-run recorded. No email was transmitted.")
            except Exception as exc: st.error(str(exc))
