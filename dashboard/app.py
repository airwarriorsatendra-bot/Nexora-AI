"""Nexora AI Streamlit entry point."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd

from dashboard.analytics import render_analytics
from dashboard.backlinks import render_backlinks
from dashboard.config import APP_DESCRIPTION, APP_NAME, LAYOUT, PAGE_ICON, PAGE_TITLE, SIDEBAR_STATE
from dashboard.database import analytics
from dashboard.explorer import render_explorer
from dashboard.metrics import render_dashboard_metrics
from dashboard.outreach import render_outreach
from dashboard.local_seo import render_local_seo
from dashboard.google_ads import render_google_ads
from dashboard.meta_ads import render_meta_ads
from dashboard.analytics_intelligence import render_analytics_intelligence
from dashboard.research import render_research
from dashboard.seo import render_seo
from dashboard.settings import render_settings
from dashboard.sidebar import render_sidebar
from dashboard.styles import apply_styles, page_header


st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout=LAYOUT,
    initial_sidebar_state=SIDEBAR_STATE,
)
apply_styles(st)

sidebar = render_sidebar()
filters = sidebar["filters"]
page_header(st, "Marketing overview", "Monitor intelligence, opportunities and campaign activity.")

data = analytics.export_dataframe()
if not data.empty:
    data = data[data["priority_score"].fillna(0) >= filters["minimum_score"]]
    if filters["keyword"]:
        pattern = filters["keyword"]
        data = data[
            data[["title", "url", "description", "notes"]]
            .fillna("")
            .astype(str)
            .apply(lambda column: column.str.contains(pattern, case=False, regex=False))
            .any(axis=1)
        ]
    if filters["category"]:
        data = data[data["category"] == filters["category"]]

if sidebar["page"] == "Dashboard":
    render_dashboard_metrics(st, data)
    left, right = st.columns((3, 2), gap="large")
    with left:
        st.subheader("Marketing intelligence")
        if data.empty:
            st.caption("Prospect score distribution becomes available after Research stores results.")
        else:
            distribution = data.assign(score_band=pd.cut(data["priority_score"].fillna(0), bins=[-1, 39, 59, 79, 100], labels=["0–39", "40–59", "60–79", "80–100"]))["score_band"].value_counts().sort_index()
            st.bar_chart(distribution, color="#5B7CFF", height=220, horizontal=True)
    with right:
        with st.container(border=True):
            st.subheader("Attention center")
            if data.empty:
                st.markdown("**Queue is clear**")
                st.caption("No prospect records require review yet.")
            else:
                high_priority = int((data["priority_score"].fillna(0) >= 80).sum())
                st.markdown("**No high-priority prospects**" if high_priority == 0 else f"**{high_priority} high-priority prospects**")
                st.caption("Open Explorer to inspect and export supported records.")
    st.subheader("Recent activity")
    if data.empty:
        st.caption("Recent workspace records will appear here after Research completes.")
    else:
        activity_columns = [column for column in ("title", "category", "priority_score", "status", "created_at") if column in data.columns]
        st.dataframe(data[activity_columns].head(5), hide_index=True, width="stretch")
    st.subheader("Platform capabilities")
    with st.container(horizontal=True):
        for label, value in (("Research", "AVAILABLE"), ("SEO", "AVAILABLE"), ("Backlinks", "AVAILABLE"), ("Outreach", "DRY RUN"), ("Google Ads", "IMPORT"), ("Meta Ads", "IMPORT"), ("Analytics", "AVAILABLE")):
            st.metric(label, value, border=True)
elif sidebar["page"] == "Research":
    render_research()
elif sidebar["page"] == "SEO":
    render_seo()
elif sidebar["page"] == "Local SEO":
    render_local_seo()
elif sidebar["page"] == "Google Ads":
    render_google_ads()
elif sidebar["page"] == "Meta Ads":
    render_meta_ads()
elif sidebar["page"] == "Backlinks":
    render_backlinks()
elif sidebar["page"] == "Explorer":
    render_explorer(st, data)
elif sidebar["page"] == "Outreach":
    render_outreach(st, data)
elif sidebar["page"] == "Analytics":
    render_analytics_intelligence()
elif sidebar["page"] == "Settings":
    render_settings(st)

st.divider()
with st.container(horizontal=True, horizontal_alignment="distribute"):
    st.caption("Nexora AI")
    st.caption("AI-powered digital marketing platform")
    st.caption("Version 1.0.0")
