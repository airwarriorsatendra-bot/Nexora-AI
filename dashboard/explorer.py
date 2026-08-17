"""Dedicated prospect data workspace."""

from __future__ import annotations

import streamlit as st


def render_explorer(st, dataframe) -> None:
    st.subheader("Prospect Explorer")
    st.caption("Search, filter and export persisted marketing opportunities.")
    if dataframe is None or dataframe.empty:
        st.info("No prospects available. Run Research to populate this workspace.")
        return
    left, middle, right = st.columns((3, 2, 2))
    search = left.text_input("Search", placeholder="Title, domain or category", key="explorer-search")
    categories = ["All", *sorted(value for value in dataframe.get("category", []).dropna().unique() if value)]
    category = middle.selectbox("Category", categories, key="explorer-category")
    minimum_score = right.slider("Minimum AI score", 0, 100, 0, key="explorer-score")
    filtered = dataframe[dataframe["priority_score"].fillna(0) >= minimum_score].copy()
    if category != "All": filtered = filtered[filtered["category"] == category]
    if search:
        filtered = filtered[filtered.astype(str).apply(lambda row: row.str.contains(search, case=False, regex=False)).any(axis=1)]
    st.caption(f"{len(filtered):,} results")
    columns = [column for column in ("title", "url", "category", "priority_score", "status") if column in filtered.columns]
    st.dataframe(filtered[columns], hide_index=True, width="stretch", height=420)
    st.download_button("Export results CSV", filtered.to_csv(index=False), "nexora_prospects.csv", "text/csv")
