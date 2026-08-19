"""Persistent product navigation; filters remain in the Explorer workspace."""

from __future__ import annotations

import streamlit as st


NAVIGATION = (
    ("OVERVIEW", (("Dashboard", "dashboard"),)),
    ("INTELLIGENCE", (("Research", "travel_explore"), ("SEO", "search"), ("Local SEO", "location_on"), ("Backlinks", "link"))),
    ("ACQUISITION", (("Outreach", "outgoing_mail"), ("Google Ads", "ads_click"), ("Meta Ads", "campaign"))),
    ("INSIGHTS", (("Analytics", "insights"), ("Explorer", "manage_search"))),
    ("SYSTEM", (("Settings", "settings"),)),
)


def render_sidebar() -> dict[str, object]:
    st.session_state.setdefault("nexora_navigation_page", "Dashboard")
    with st.sidebar:
        st.markdown("### Nexora AI")
        st.caption("Powered by Nexora Digital Hub")
        st.caption("AI Marketing Intelligence · BETA")
        st.divider()
        for group, entries in NAVIGATION:
            st.caption(group)
            for page, icon in entries:
                active = st.session_state.nexora_navigation_page == page
                if st.button(f":material/{icon}:  {page}", key=f"nexora_nav_{page}", type="primary" if active else "secondary", width="stretch"):
                    st.session_state.nexora_navigation_page = page
                    st.rerun()
        st.divider()
        st.caption("Single-workspace beta · import and dry-run capabilities are clearly labelled in their modules.")
    return {"page": st.session_state.nexora_navigation_page, "filters": {"keyword": "", "category": "", "minimum_score": 0}}
