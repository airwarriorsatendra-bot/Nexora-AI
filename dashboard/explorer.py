"""
==========================================================
NEXORA AI
Prospect Explorer
==========================================================
"""

import streamlit as st
import pandas as pd


def render_explorer(st, dataframe):
    """
    Display and explore prospect data.
    """

    st.subheader("🔎 Prospect Explorer")

    if dataframe is None or dataframe.empty:
        st.info("No prospects available.")
        return

    search = st.text_input(
        "Search prospects",
        placeholder="Enter title, URL, category..."
    )

    filtered = dataframe.copy()

    if search:
        search = search.lower()

        filtered = filtered[
            filtered.astype(str)
            .apply(
                lambda row: row.str.lower().str.contains(search),
                axis=1,
            )
            .any(axis=1)
        ]

    st.write(f"**Results:** {len(filtered)}")

    st.dataframe(
        filtered,
        width="stretch",
        hide_index=True,
    )

    if not filtered.empty:

        st.download_button(
            label="📥 Download CSV",
            data=filtered.to_csv(index=False),
            file_name="nexora_prospects.csv",
            mime="text/csv",
        )

        with st.expander("View First Prospect"):

            first = filtered.iloc[0]

            for column in filtered.columns:

                st.markdown(
                    f"**{column}**"
                )

                st.write(first[column])
