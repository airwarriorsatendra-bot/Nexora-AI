"""Premium SEO workspace panel for persisted Search Console performance."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from dashboard.research_workflow import run_async
from dashboard.search_console_workflow import SearchConsoleDashboardWorkflow
from src.search_console.domain import ReportingPeriod, SearchConsoleProperty, SearchDimension, SearchPerformanceRecord
from src.search_console.dto import SearchAnalyticsRequest, SearchPerformanceResponse


def _records_frame(records: tuple[SearchPerformanceRecord, ...]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for record in records:
        row = {dimension.value.title(): record.dimension_value(dimension) for dimension in record.dimensions}
        row.update({"Clicks": record.clicks, "Impressions": record.impressions, "CTR": float(record.ctr), "Average position": float(record.average_position)})
        rows.append(row)
    return pd.DataFrame(rows)


def _opportunities_frame(records: tuple[SearchPerformanceRecord, ...], kind: str) -> pd.DataFrame:
    frame = _records_frame(records)
    if frame.empty:
        return frame
    frame["Opportunity type"] = "CTR opportunity" if kind == "ctr" else "Position opportunity"
    frame["Evidence"] = frame.apply(lambda row: f"{int(row['Impressions'])} impressions, {row['CTR']:.2%} CTR, average position {row['Average position']:.1f}.", axis=1)
    frame["Recommendation"] = "Review the result title and snippet against the represented search intent." if kind == "ctr" else "Review relevance, on-page coverage, and internal linking for this query or page."
    return frame


def render_search_console(workflow: SearchConsoleDashboardWorkflow | None = None) -> None:
    """Network access is available only behind the discover and refresh controls."""
    workflow = workflow or SearchConsoleDashboardWorkflow()
    st.divider()
    st.subheader("Search performance")
    st.caption("GOOGLE SEARCH CONSOLE · Read-only organic-search data. Average position is not a live ranking signal.")
    if not workflow.is_configured():
        with st.container(border=True):
            st.markdown("**Google Search Console · Not configured**")
            st.caption("Set GSC_CLIENT_ID, GSC_CLIENT_SECRET, and GSC_REFRESH_TOKEN, enable the Search Console API, and authorize a property. Nexora stores no tokens.")
        return
    st.session_state.setdefault("gsc_properties", ())
    st.session_state.setdefault("gsc_response", None)
    st.session_state.setdefault("gsc_error", None)
    controls, action = st.columns((4, 1), vertical_alignment="bottom")
    if action.button("Discover properties", key="gsc-discover", type="secondary"):
        try:
            st.session_state.gsc_properties = run_async(workflow.discover_properties())
            st.session_state.gsc_error = None
        except Exception:
            st.session_state.gsc_error = "Google Search Console properties could not be loaded. Verify account access and try again."
    if st.session_state.gsc_error:
        st.error(st.session_state.gsc_error)
    properties: tuple[SearchConsoleProperty, ...] = st.session_state.gsc_properties
    if not properties:
        st.info("Discover the Search Console properties authorized for this account before refreshing performance data.")
        return
    choices = {item.site_url: item for item in properties}
    default_end = date.today() - timedelta(days=1)
    default_start = default_end - timedelta(days=27)
    with st.form("gsc-refresh", border=True):
        property_column, dates_column, action_column = st.columns((3, 3, 1), vertical_alignment="bottom")
        site_url = property_column.selectbox("Property", tuple(choices), key="gsc-property")
        selected_dates = dates_column.date_input("Reporting period", value=(default_start, default_end), max_value=default_end, key="gsc-period")
        submitted = action_column.form_submit_button("Refresh data", type="primary")
    if submitted:
        if not isinstance(selected_dates, tuple) or len(selected_dates) != 2:
            st.error("Select both a start and end date.")
        else:
            try:
                request = SearchAnalyticsRequest(property=choices[site_url], period=ReportingPeriod(start_date=selected_dates[0], end_date=selected_dates[1]))
                with st.status("Refreshing Search Console data…", expanded=False) as status:
                    st.session_state.gsc_response = run_async(workflow.refresh(request))
                    status.update(label="Search Console data refreshed", state="complete")
            except Exception:
                st.error("Search Console data could not be refreshed. Check property authorization, credentials, and the selected period.")
    response = st.session_state.gsc_response
    if not isinstance(response, SearchPerformanceResponse):
        return
    totals = response.snapshot.totals
    with st.container(horizontal=True):
        st.metric("Organic clicks", totals.clicks, border=True)
        st.metric("Organic impressions", totals.impressions, border=True)
        st.metric("Organic CTR", f"{totals.ctr:.2%}", border=True)
        st.metric("Average position", f"{totals.average_position:.1f}", border=True)
    date_frame = _records_frame(response.date_records)
    if not date_frame.empty and "Date" in date_frame.columns:
        st.subheader("Performance over time")
        st.line_chart(date_frame, x="Date", y=["Clicks", "Impressions"])
    tabs = st.tabs(["Top queries", "Top pages", "Opportunities"])
    with tabs[0]:
        frame = _records_frame(response.top_queries)
        if frame.empty:
            st.info("No query rows were returned for this selected period.")
        else:
            st.dataframe(frame, hide_index=True, column_config={"CTR": st.column_config.NumberColumn(format="percent"), "Average position": st.column_config.NumberColumn(format="%.1f")})
            st.download_button("Export query CSV", frame.to_csv(index=False), "nexora_gsc_queries.csv", "text/csv")
    with tabs[1]:
        frame = _records_frame(response.top_pages)
        if frame.empty:
            st.info("No page rows were returned for this selected period.")
        else:
            st.dataframe(frame, hide_index=True, column_config={"CTR": st.column_config.NumberColumn(format="percent"), "Average position": st.column_config.NumberColumn(format="%.1f")})
            st.download_button("Export page CSV", frame.to_csv(index=False), "nexora_gsc_pages.csv", "text/csv")
    with tabs[2]:
        frame = pd.concat((_opportunities_frame(response.ctr_opportunities, "ctr"), _opportunities_frame(response.position_opportunities, "position")), ignore_index=True)
        if frame.empty:
            st.success("No dataset-relative CTR or position opportunities were identified in this refresh.")
        else:
            st.caption("Opportunities use the selected dataset’s median impressions and lower CTR quartile; they are observations, not ranking guarantees.")
            st.dataframe(frame, hide_index=True, column_config={"CTR": st.column_config.NumberColumn(format="percent"), "Average position": st.column_config.NumberColumn(format="%.1f")})
            st.download_button("Export opportunities CSV", frame.to_csv(index=False), "nexora_gsc_opportunities.csv", "text/csv")
