"""
==========================================================
NEXORA AI
Analytics
==========================================================
"""

import streamlit as st


def render_analytics(st, dataframe):
    """
    Render Analytics Dashboard
    """

    st.subheader("📊 Analytics")

    if dataframe is None or dataframe.empty:
        st.info("No data available.")
        return

    total = len(dataframe)

    avg_score = 0
    if "priority_score" in dataframe.columns:
        avg_score = round(
            dataframe["priority_score"].fillna(0).mean(),
            1,
        )

    col1, col2 = st.columns(2)

    col1.metric(
        "Total Prospects",
        total,
    )

    col2.metric(
        "Average AI Score",
        avg_score,
    )

    st.divider()

    if "category" in dataframe.columns:

        st.subheader("Prospects by Category")

        category = (
            dataframe["category"]
            .fillna("Unknown")
            .value_counts()
        )

        st.bar_chart(category)

    if "status" in dataframe.columns:

        st.subheader("Prospects by Status")

        status = (
            dataframe["status"]
            .fillna("Unknown")
            .value_counts()
        )

        st.bar_chart(status)

    st.divider()

    st.subheader("Raw Data")

    st.dataframe(
        dataframe,
        width="stretch",
        hide_index=True,
    )
