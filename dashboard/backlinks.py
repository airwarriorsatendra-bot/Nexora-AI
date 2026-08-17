"""Streamlit presentation for evidence-based backlink intelligence."""

from __future__ import annotations

import asyncio
from typing import Any

import streamlit as st

from dashboard.backlinks_workflow import BacklinksDashboardWorkflow, backlinks_to_dataframe
from src.backlinks.dto.backlink_discovery import BacklinkDiscoveryResponse
from src.backlinks.dto.backlink_verification import BacklinkVerificationResponse


def _run_async(coroutine: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)
    raise RuntimeError("Backlink operations cannot start while another event loop is active.")


def _initialize_state() -> None:
    st.session_state.setdefault("backlink_discovery_response", None)
    st.session_state.setdefault("backlink_verification_response", None)
    st.session_state.setdefault("backlink_persisted", None)


def render_backlinks(workflow: BacklinksDashboardWorkflow | None = None) -> None:
    """Render only implemented imported-opportunity and HTML-verification capabilities."""
    _initialize_state()
    workflow = workflow or BacklinksDashboardWorkflow()
    st.subheader("Backlink Intelligence")
    st.caption("Opportunities and verified links are deliberately separate evidence types.")

    with st.form("backlink-discovery", border=True):
        target_url = st.text_input("Target URL", placeholder="https://example.com/guide", key="backlink-target-url")
        candidates = st.text_area("Opportunity URLs", placeholder="One URL per line", key="backlink-candidate-urls")
        discover_submitted = st.form_submit_button("Save opportunities", type="primary")
    if discover_submitted:
        values = [line.strip() for line in candidates.splitlines() if line.strip()]
        try:
            st.session_state.backlink_discovery_response = _run_async(workflow.discover(target_url, values))
        except Exception:
            st.error("Opportunities could not be saved. Use absolute HTTP(S) URLs.")

    discovery = st.session_state.backlink_discovery_response
    if isinstance(discovery, BacklinkDiscoveryResponse):
        (st.success if discovery.success else st.error)(discovery.message)
        for error in discovery.errors:
            st.caption(error)

    st.subheader("Verified backlinks")
    with st.form("backlink-verification", border=True):
        source_url = st.text_input("Source page URL", placeholder="https://publisher.example/article", key="backlink-source-url")
        verification_target = st.text_input("Target URL to verify", value=target_url, key="backlink-verification-target")
        verify_submitted = st.form_submit_button("Verify backlink")
    if verify_submitted:
        try:
            st.session_state.backlink_verification_response = _run_async(workflow.verify(source_url, verification_target))
        except Exception:
            st.error("Verification could not be started. Use absolute HTTP(S) URLs.")

    verification = st.session_state.backlink_verification_response
    if isinstance(verification, BacklinkVerificationResponse):
        (st.success if verification.success else st.error)(verification.message)
        if verification.backlink is not None:
            st.json(verification.backlink.model_dump(mode="json"))
        for error in verification.errors:
            st.caption(error)

    if target_url and st.button("Refresh verified-link history", key="backlink-refresh"):
        try:
            st.session_state.backlink_persisted = _run_async(workflow.list_backlinks(target_url))
        except Exception:
            st.error("Backlink history could not be loaded.")
    persisted = st.session_state.backlink_persisted
    if isinstance(persisted, list):
        frame = backlinks_to_dataframe(persisted)
        st.subheader("Verified-link history")
        if frame.empty:
            st.info("No backlink records are stored for this target domain.")
        else:
            st.dataframe(frame, hide_index=True, key="backlink-history")
            st.download_button("Export backlink CSV", frame.to_csv(index=False), "nexora_backlinks.csv", "text/csv", key="backlink-export")
