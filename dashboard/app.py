"""Nexora AI Streamlit entry point."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

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
page_header(st, APP_NAME, APP_DESCRIPTION)

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
    render_explorer(st, data)
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
