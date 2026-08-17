"""Navigation and legacy-prospect filters for the Streamlit dashboard."""

from __future__ import annotations

import streamlit as st

from dashboard.database import utility


def render_sidebar() -> dict[str, object]:
    """Render application navigation and filters without starting research work."""
    st.sidebar.title("Nexora AI")
    st.sidebar.caption("AI digital marketing platform")
    st.sidebar.divider()

    page = st.sidebar.selectbox(
        "Workspace",
        ["Dashboard", "Research", "SEO", "Local SEO", "Google Ads", "Meta Ads", "Backlinks", "Explorer", "Outreach", "Analytics", "Settings"],
        label_visibility="collapsed",
    )

    st.sidebar.divider()
    st.sidebar.subheader("Prospect search")
    keyword = st.sidebar.text_input(
        "Search existing prospects",
        placeholder="Search title, URL or notes…",
    )
    categories = ["All"]
    try:
        categories.extend(value for value in utility.distinct_values("prospects", "category") if value)
    except Exception:
        # Legacy dashboard filtering remains usable even if its store is unavailable.
        pass
    category = st.sidebar.selectbox("Category", categories)
    minimum_score = st.sidebar.slider("Minimum AI score", 0, 100, 0)

    return {
        "page": page,
        "filters": {
            "keyword": keyword,
            "category": "" if category == "All" else category,
            "minimum_score": minimum_score,
        },
    }
