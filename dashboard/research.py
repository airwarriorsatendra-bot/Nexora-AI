"""Streamlit presentation for the source-layer Research workflow."""

from __future__ import annotations

import logging
from typing import Any

import streamlit as st
from pydantic import ValidationError as PydanticValidationError

from dashboard.research_workflow import (
    ResearchDashboardWorkflow,
    ResearchFormValues,
    prospects_to_dataframe,
    run_async,
    split_lines,
)
from src.core.enums import ResearchMode
from src.core.exceptions import ConfigurationError, NexoraError
from src.research.dto.response.research_response import ResearchResponse


logger = logging.getLogger("nexora.dashboard.research")


def _initialize_state() -> None:
    st.session_state.setdefault("research_response", None)
    st.session_state.setdefault("research_persisted", None)
    st.session_state.setdefault("research_error", "")
    st.session_state.setdefault("research_form_values", None)


def _render_response(response: ResearchResponse) -> None:
    progress = response.progress
    if progress is not None:
        st.progress(progress.progress_ratio, text=progress.message or "Research completed.")
        with st.container(horizontal=True):
            st.metric("Phase", progress.phase.value.replace("_", " "), border=True)
            st.metric("Processed", f"{progress.processed}/{progress.total}", border=True)
            st.metric("Completion", f"{progress.percentage:.0f}%", border=True)

    statistics = response.statistics
    with st.container(horizontal=True):
        st.metric("Results", response.total_results, border=True)
        st.metric("Prospects saved", statistics.prospects_saved, border=True)
        st.metric("Average AI score", f"{statistics.average_ai_score:.1f}", border=True)
        st.metric("Elapsed", f"{statistics.elapsed_seconds:.1f}s", border=True)

    for warning in response.warnings:
        st.warning(warning)
    for error in response.errors:
        st.error(error)

    if response.success:
        st.success(response.message or "Research completed.")
    elif not response.errors:
        st.info(response.message or "Research completed without results.")

    _render_prospects("Research results", response.results, "research-results")


def _render_prospects(title: str, prospects: list[Any], key_prefix: str) -> None:
    st.subheader(title)
    dataframe = prospects_to_dataframe(prospects)
    if dataframe.empty:
        st.info("No prospects are available yet.")
        return

    st.dataframe(dataframe, hide_index=True, key=f"{key_prefix}-table")
    st.download_button(
        "Export CSV",
        data=dataframe.to_csv(index=False),
        file_name="nexora_research_prospects.csv",
        mime="text/csv",
        key=f"{key_prefix}-export",
    )


def render_research(workflow: ResearchDashboardWorkflow | None = None) -> None:
    """Render the Research page without legacy agents, SQL, or provider calls."""
    _initialize_state()
    workflow = workflow or ResearchDashboardWorkflow()

    st.subheader("Research")
    st.caption("Discover, enrich, persist, and export backlink opportunities.")

    search_providers = workflow.available_search_providers()
    ai_providers = workflow.available_ai_providers()
    if not search_providers or not ai_providers:
        st.error("Research is unavailable: configure a supported search and AI provider in the environment.")
        return

    with st.form("research-request", border=True):
        industry = st.text_input("Industry or niche", key="research-industry")
        research_mode = st.selectbox(
            "Research mode",
            options=list(ResearchMode),
            format_func=lambda mode: mode.value.replace("_", " "),
            key="research-mode",
        )
        search_provider = st.selectbox(
            "Search provider",
            options=list(search_providers),
            format_func=lambda provider: provider.value,
            key="research-search-provider",
        )
        ai_provider = st.selectbox("AI provider", options=list(ai_providers), key="research-ai-provider")

        location_left, location_right = st.columns(2)
        country = location_left.text_input("Country", key="research-country")
        state = location_right.text_input("State or region", key="research-state")
        city = location_left.text_input("City", key="research-city")
        max_results = location_right.number_input(
            "Maximum results", min_value=1, max_value=1000, value=20, key="research-max-results"
        )

        custom_queries = st.text_area("Custom queries", key="research-custom-queries")
        included_domains = st.text_area("Included domains", key="research-included-domains")
        excluded_domains = st.text_area("Excluded domains", key="research-excluded-domains")
        with st.expander("Research options"):
            enable_crawling = st.checkbox("Enable crawling", value=True, key="research-enable-crawling")
            enable_ai_analysis = st.checkbox("Enable AI analysis", value=True, key="research-enable-ai")
            extract_contact_info = st.checkbox("Extract contact information", value=True, key="research-contact-info")
            extract_social_links = st.checkbox("Extract social links", value=True, key="research-social-links")
            include_subdomains = st.checkbox("Include subdomains", key="research-subdomains")
            follow_redirects = st.checkbox("Follow redirects", value=True, key="research-redirects")
        submitted = st.form_submit_button("Start research", type="primary")

    if submitted:
        values = ResearchFormValues(
            industry=industry,
            research_mode=research_mode,
            search_provider=search_provider,
            ai_provider=ai_provider,
            country=country,
            state=state,
            city=city,
            max_results=int(max_results),
            custom_queries=split_lines(custom_queries),
            included_domains=split_lines(included_domains),
            excluded_domains=split_lines(excluded_domains),
            enable_crawling=enable_crawling,
            enable_ai_analysis=enable_ai_analysis,
            extract_contact_info=extract_contact_info,
            extract_social_links=extract_social_links,
            include_subdomains=include_subdomains,
            follow_redirects=follow_redirects,
        )
        st.session_state.research_form_values = values
        try:
            with st.status("Research is running…", expanded=True) as status:
                response = run_async(workflow.execute(values))
                st.session_state.research_response = response
                st.session_state.research_error = ""
                status.update(label="Research completed", state="complete")
        except (ConfigurationError, NexoraError, PydanticValidationError, RuntimeError) as error:
            logger.exception("Research dashboard action failed.")
            st.session_state.research_error = str(error)
        except Exception:
            logger.exception("Unexpected research dashboard failure.")
            st.session_state.research_error = "Research could not be completed. Please try again."

    if st.session_state.research_error:
        st.error(st.session_state.research_error)
    response = st.session_state.research_response
    if isinstance(response, ResearchResponse):
        _render_response(response)

    values = st.session_state.research_form_values
    if isinstance(values, ResearchFormValues) and st.button("Refresh persisted research prospects"):
        try:
            st.session_state.research_persisted = run_async(workflow.list_persisted(values))
        except (ConfigurationError, NexoraError, RuntimeError) as error:
            logger.exception("Research prospect refresh failed.")
            st.error(str(error))
        except Exception:
            logger.exception("Unexpected research prospect refresh failure.")
            st.error("Persisted research prospects could not be loaded.")

    persisted = st.session_state.research_persisted
    if isinstance(persisted, list):
        _render_prospects("Persisted research prospects", persisted, "research-persisted")
