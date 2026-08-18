"""Streamlit SEO Intelligence workspace with audit and search-performance views."""

from __future__ import annotations

import asyncio
from typing import Any

import pandas as pd
import streamlit as st

from dashboard.search_console import render_search_console
from dashboard.seo_workflow import SEODashboardWorkflow
from dashboard.rank_tracking import render_rank_tracking
from dashboard.rank_tracking_workflow import RankTrackingDashboardWorkflow
from dashboard.site_crawl import render_site_crawl
from src.seo.domain.seo_intelligence import SEOIntelligenceReport, SEOOpportunity
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


def _opportunity_frame(items: tuple[SEOOpportunity, ...], tracked: dict[str, tuple[Any, Any]] | None = None) -> pd.DataFrame:
    tracked = tracked or {}
    return pd.DataFrame([{"Priority": item.priority_score, "Type": item.opportunity_type.value.replace("_", " ").title(), "Subject": item.subject, "Clicks": item.clicks, "Impressions": item.impressions, "CTR": float(item.ctr), "GSC Avg Position": float(item.average_position), "Tracked SERP Position": tracked[item.subject][0].position_label if item.subject in tracked else "NOT AVAILABLE", "Tracked Change": tracked[item.subject][1].change_type.value if item.subject in tracked else "NOT AVAILABLE", "Trend": item.comparison.trend.value if item.comparison else "NOT AVAILABLE", "Evidence": " • ".join(item.evidence), "Recommended action": item.recommendation} for item in items])


def _render_intelligence(workflow: SEODashboardWorkflow) -> None:
    st.session_state.setdefault("seo_intelligence_report", None)
    st.caption("Derived locally from persisted GSC and period-matched GA4 snapshots. No external refresh runs here.")
    if st.button("Load persisted intelligence", key="seo-intelligence-load", type="primary"):
        try:
            st.session_state.seo_intelligence_report = _run_async(workflow.intelligence())
        except Exception:
            st.error("Persisted SEO intelligence could not be loaded.")
    report = st.session_state.seo_intelligence_report
    if not isinstance(report, SEOIntelligenceReport):
        st.info("Load persisted intelligence after refreshing Search Performance. No metrics are fabricated when data is unavailable.")
        return
    opportunities = report.opportunities
    with st.container(horizontal=True):
        st.metric("SEO opportunities", len(opportunities), border=True)
        st.metric("High priority", sum(item.priority_score >= 60 for item in opportunities), border=True)
        st.metric("Striking distance", sum(item.opportunity_type.value == "STRIKING_DISTANCE" for item in opportunities), border=True)
        st.metric("CTR opportunities", sum(item.opportunity_type.value == "LOW_CTR" for item in opportunities), border=True)
    for note in report.notes:
        st.info(note)
    rank_workflow = RankTrackingDashboardWorkflow()
    try:
        rank_data = _run_async(rank_workflow.snapshot())
        tracked = {keyword.keyword: (check, change) for keyword, check, change in rank_data["rows"] if keyword}
    except Exception:
        tracked = {}
    frame = _opportunity_frame(opportunities, tracked)
    st.subheader("Priority opportunities")
    if frame.empty:
        st.info("No deterministic opportunities were identified in persisted source snapshots.")
        return
    st.dataframe(frame.head(25), hide_index=True, width="stretch", column_config={"CTR": st.column_config.NumberColumn(format="percent"), "Evidence": st.column_config.TextColumn(width="large"), "Recommended action": st.column_config.TextColumn(width="large")})
    query_frame, page_frame = _opportunity_frame(report.query_opportunities, tracked), _opportunity_frame(report.page_opportunities, tracked)
    query_candidates = tuple(item for item in report.query_opportunities if item.subject_kind == "query")
    if query_candidates:
        with st.form("seo-opportunity-to-rank"):
            candidate = st.selectbox("GSC opportunity", query_candidates, format_func=lambda item: item.subject)
            target = st.text_input("Target domain for tracking")
            promote = st.form_submit_button("Add to Rank Tracker")
        if promote:
            try:
                _run_async(rank_workflow.add(candidate.subject, target, "", "US", "desktop", candidate))
                st.success("GSC opportunity added to Rank Tracking. GSC and tracked positions remain separate.")
            except Exception:
                st.error("The selected opportunity could not be added to Rank Tracking.")
    query_tab, page_tab, bridge_tab = st.tabs(["Query intelligence", "Page intelligence", "GSC + GA4 insights"])
    with query_tab:
        _render_filtered("Query opportunities", query_frame, "query")
    with page_tab:
        _render_filtered("Page opportunities", page_frame, "page")
    with bridge_tab:
        bridge = _opportunity_frame(report.gsc_ga4_insights)
        if bridge.empty:
            st.info("No period-matched URL evidence supports a GSC + GA4 insight.")
        else:
            st.dataframe(bridge, hide_index=True, width="stretch")
    st.download_button("Export all opportunities CSV", frame.to_csv(index=False), "nexora_seo_opportunities.csv", "text/csv")
    st.download_button("Export query opportunities CSV", query_frame.to_csv(index=False), "nexora_seo_query_opportunities.csv", "text/csv")
    st.download_button("Export page opportunities CSV", page_frame.to_csv(index=False), "nexora_seo_page_opportunities.csv", "text/csv")


def _render_filtered(label: str, frame: pd.DataFrame, key: str) -> None:
    if frame.empty:
        st.info(f"No persisted {key} opportunity evidence is available.")
        return
    types = st.multiselect(f"{label} types", sorted(frame["Type"].unique()), default=sorted(frame["Type"].unique()), key=f"seo-{key}-types")
    minimum = st.number_input(f"Minimum impressions ({key})", min_value=0, value=0, key=f"seo-{key}-minimum")
    search = st.text_input(f"Search {key}s", key=f"seo-{key}-search")
    filtered = frame[frame["Type"].isin(types) & (frame["Impressions"] >= minimum)]
    if search:
        filtered = filtered[filtered["Subject"].str.contains(search, case=False, regex=False)]
    st.dataframe(filtered, hide_index=True, width="stretch", column_config={"CTR": st.column_config.NumberColumn(format="percent"), "Evidence": st.column_config.TextColumn(width="large"), "Recommended action": st.column_config.TextColumn(width="large")})


def render_seo(workflow: SEODashboardWorkflow | None = None) -> None:
    """Present technical auditing and read-only organic performance as peer views."""
    workflow = workflow or SEODashboardWorkflow()
    st.subheader("SEO Intelligence")
    st.caption("Technical audits and Google Search performance remain distinct evidence layers.")
    audit_tab, performance_tab, intelligence_tab, rank_tab, crawl_tab = st.tabs(["Technical audit", "Search performance", "SEO intelligence", "Rank tracking", "Site crawl"])
    with audit_tab:
        _render_technical_audit(workflow)
    with performance_tab:
        render_search_console()
    with intelligence_tab:
        _render_intelligence(workflow)
    with rank_tab:
        render_rank_tracking()
    with crawl_tab:
        render_site_crawl()
