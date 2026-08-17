"""Streamlit SEO audit presentation backed by the source-layer service."""

from __future__ import annotations

import asyncio
from typing import Any

import pandas as pd
import streamlit as st

from dashboard.seo_workflow import SEODashboardWorkflow
from src.seo.dto.seo_audit_response import SEOAuditResponse


def _run_async(coroutine: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)
    raise RuntimeError("SEO audit cannot start while another event loop is active.")


def _issues_frame(response: SEOAuditResponse) -> pd.DataFrame:
    if response.audit is None:
        return pd.DataFrame()
    return pd.DataFrame([issue.model_dump(mode="json") for issue in response.audit.issues])


def render_seo(workflow: SEODashboardWorkflow | None = None) -> None:
    """Render one form-driven SEO audit without import-time network activity."""
    st.session_state.setdefault("seo_response", None)
    workflow = workflow or SEODashboardWorkflow()
    st.subheader("SEO audit")
    st.caption("Deterministic technical, on-page, content, structured-data, image, and link checks.")

    with st.form("seo-audit", border=True):
        url = st.text_input("Page URL", placeholder="https://example.com/page", key="seo-url")
        submitted = st.form_submit_button("Run SEO audit", type="primary")
    if submitted:
        try:
            with st.status("SEO audit is running…", expanded=True) as status:
                st.session_state.seo_response = _run_async(workflow.execute(url))
                status.update(label="SEO audit completed", state="complete")
        except Exception:
            st.error("SEO audit could not be completed. Check the URL and try again.")
            return

    response = st.session_state.seo_response
    if not isinstance(response, SEOAuditResponse):
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
    scores = pd.DataFrame(audit.category_scores.items(), columns=["Category", "Score"])
    st.subheader("Category scores")
    st.bar_chart(scores, x="Category", y="Score")
    issues = _issues_frame(response)
    st.subheader("Findings")
    if issues.empty:
        st.success("No deterministic issues were found.")
    else:
        severity_filter = st.multiselect("Severity", sorted(issues["severity"].unique()), default=sorted(issues["severity"].unique()))
        filtered = issues[issues["severity"].isin(severity_filter)]
        st.dataframe(filtered, hide_index=True, key="seo-findings")
        st.download_button("Export findings CSV", filtered.to_csv(index=False), "nexora_seo_findings.csv", "text/csv")
