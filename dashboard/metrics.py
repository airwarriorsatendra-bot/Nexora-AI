"""Executive dashboard metrics derived only from persisted prospect data."""

from __future__ import annotations


def render_dashboard_metrics(st, dataframe) -> None:
    """Render a compact, honest premium KPI row."""
    if dataframe is None or dataframe.empty:
        st.info("No prospects yet. Start Research to build your opportunity pipeline.")
        return
    total = len(dataframe)
    high_priority = len(dataframe[dataframe["priority_score"] >= 80])
    contacted = len(dataframe[dataframe["status"] == "Contacted"]) if "status" in dataframe.columns else 0
    average_score = round(dataframe["priority_score"].fillna(0).mean(), 1)
    st.caption("EXECUTIVE OVERVIEW")
    with st.container(horizontal=True):
        st.metric("Prospects", f"{total:,}", border=True)
        st.metric("High priority", f"{high_priority:,}", border=True)
        st.metric("Contacted", f"{contacted:,}", border=True)
        st.metric("Average AI score", average_score, border=True)
