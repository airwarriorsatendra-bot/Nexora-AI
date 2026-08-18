"""Streamlit SEO Intelligence workspace with audit and search-performance views."""

from __future__ import annotations

import asyncio
from typing import Any

import pandas as pd
import streamlit as st

from dashboard.search_console import render_search_console
from dashboard.seo_workflow import SEODashboardWorkflow
from src.seo.dto.seo_audit_response import SEOAuditResponse


def _run_async(coroutine: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)
    raise RuntimeError("SEO audit cannot start while another event loop is active.")


def _issues_frame(response: SEOAuditResponse) -> pd.DataFrame:
    return pd.DataFrame() if response.audit is None else pd.DataFrame([issue.model_dump(mode="json") for issue in response.audit.issues])


def _render_technical_audit(workflow: SEODashboardWorkflow) -> None:
    """Render the existing deterministic audit workflow without changing its data contract."""
    st.session_state.setdefault("seo_response", None)
    st.caption("Deterministic technical, on-page, content and structured-data auditing.")
    with st.form("seo-audit", border=True):
        input_column, action_column = st.columns((4, 1), vertical_alignment="bottom")
        url = input_column.text_input("Website URL", placeholder="https://example.com/page", key="seo-url")
        submitted = action_column.form_submit_button("Run audit", type="primary")
    if submitted:
        try:
            with st.status("SEO audit is running…", expanded=True) as status:
                st.session_state.seo_response = _run_async(workflow.execute(url))
                status.update(label="SEO audit completed", state="complete")
        except Exception:
            st.error("SEO audit could not be completed. Check the URL and try again.")

    response = st.session_state.seo_response
    if not isinstance(response, SEOAuditResponse):
        st.info("Run a technical audit to view scores, findings, and exportable recommendations.")
        return
    if not response.success or response.audit is None:
        st.error(response.message)
        for error in response.errors:
            st.caption(error)
        return

    audit = response.audit
    with st.container(horizontal=True):
        st.metric("Overall score", f"{audit.overall_score:.0f}", border=True)
        st.metric("Issues", audit.issue_count, border=True)
        st.metric("Words", audit.metrics.get("word_count", 0), border=True)
        st.metric("Internal links", audit.metrics.get("internal_links", 0), border=True)

    st.subheader("Audit coverage")
    scores = pd.DataFrame(audit.category_scores.items(), columns=["Category", "Score"])
    st.bar_chart(scores, x="Category", y="Score", horizontal=True, sort=False, color="#5B7CFF", height=240)

    st.subheader("Findings and recommendations")
    issues = _issues_frame(response)
    if issues.empty:
        st.success("No deterministic issues were found.")
        return
    severity_filter = st.multiselect("Severity", sorted(issues["severity"].unique()), default=sorted(issues["severity"].unique()))
    filtered = issues[issues["severity"].isin(severity_filter)]
    st.dataframe(
        filtered,
        hide_index=True,
        key="seo-findings",
        column_config={
            "description": st.column_config.TextColumn("Description", width="large"),
            "recommendation": st.column_config.TextColumn("Recommendation", width="large"),
            "evidence": st.column_config.TextColumn("Evidence", width="large"),
        },
    )
    st.download_button("Export findings CSV", filtered.to_csv(index=False), "nexora_seo_findings.csv", "text/csv")


def render_seo(workflow: SEODashboardWorkflow | None = None) -> None:
    """Present technical auditing and read-only organic performance as peer views."""
    workflow = workflow or SEODashboardWorkflow()
    st.subheader("SEO Intelligence")
    st.caption("Technical audits and Google Search performance remain distinct evidence layers.")
    audit_tab, performance_tab = st.tabs(["Technical audit", "Search performance"])
    with audit_tab:
        _render_technical_audit(workflow)
    with performance_tab:
        render_search_console()
