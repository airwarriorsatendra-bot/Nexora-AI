"""Source-layer cross-channel KPI presentation with honest export semantics."""

from __future__ import annotations

import streamlit as st

from dashboard.analytics_workflow import AnalyticsDashboardWorkflow, insights_to_dataframe, kpis_to_dataframe
from dashboard.research_workflow import run_async


def render_analytics_intelligence(workflow: AnalyticsDashboardWorkflow | None = None) -> None:
    st.subheader("Marketing intelligence")
    st.caption("KPIs retain source, reporting period, and currency. Cross-platform conversions are source-attributed and not deduplicated.")
    workflow = workflow or AnalyticsDashboardWorkflow()
    st.session_state.setdefault("analytics_report", None)
    if st.button("Refresh available source snapshots"):
        try:
            st.session_state.analytics_report = run_async(workflow.latest_report())
        except Exception as exc:
            st.error(f"Unable to refresh Analytics snapshots: {exc}")
    report = st.session_state.analytics_report
    if report is None:
        st.info("No persisted Google Ads or Meta Ads snapshots are available yet.")
        return
    available_sources = sorted({kpi.source_module for kpi in report.kpis})
    sources = tuple(st.multiselect("Source modules", available_sources, default=available_sources))
    frame = kpis_to_dataframe(report, sources)
    if frame.empty:
        st.info("No KPIs match the selected sources.")
    else:
        st.dataframe(frame, hide_index=True)
        st.download_button("Export KPI CSV", frame.to_csv(index=False), "nexora_analytics_kpis.csv", "text/csv")
    insight_frame = insights_to_dataframe(report)
    if not insight_frame.empty:
        st.subheader("Evidence-backed insights")
        st.dataframe(insight_frame, hide_index=True)
        st.download_button("Export insights CSV", insight_frame.to_csv(index=False), "nexora_analytics_insights.csv", "text/csv")
