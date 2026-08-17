"""
==========================================================
NEXORA AI
Dashboard Metrics
==========================================================
"""

import streamlit as st


def render_dashboard_metrics(st, dataframe):
    """
    Render dashboard KPI cards.
    """

    if dataframe is None or dataframe.empty:

        st.warning("No prospects found.")

        return

    total = len(dataframe)

    high_priority = len(
        dataframe[
            dataframe["priority_score"] >= 80
        ]
    )

    average_score = round(
        dataframe["priority_score"].fillna(0).mean(),
        1,
    )

    contacted = 0

    if "status" in dataframe.columns:

        contacted = len(
            dataframe[
                dataframe["status"] == "Contacted"
            ]
        )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "🌐 Prospects",
        f"{total:,}",
    )

    col2.metric(
        "⭐ High Priority",
        f"{high_priority:,}",
    )

    col3.metric(
        "📧 Contacted",
        f"{contacted:,}",
    )

    col4.metric(
        "🤖 Avg AI Score",
        average_score,
    )

    st.divider()