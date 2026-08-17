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
    columns = st.columns(4, gap="small")
    for column, label, value, context in zip(columns, ("Prospects", "High priority", "Contacted", "Average AI score"), (f"{total:,}", f"{high_priority:,}", f"{contacted:,}", average_score), ("Discovered records", "Ready for review", "Recorded outreach status", "From persisted prospects")):
        with column:
            st.metric(label, value, border=True)
            st.caption(context)
