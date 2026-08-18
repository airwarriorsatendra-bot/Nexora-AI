"""Persisted-evidence AEO/GEO readiness workspace."""
from __future__ import annotations

import asyncio

import pandas as pd
import streamlit as st

from dashboard.aeo_geo_workflow import AEOGEODashboardWorkflow
from src.aeo_geo.domain import AEOGEOReport
from src.aeo_geo.service import AEOGEOService


def _run(coroutine):
    return asyncio.run(coroutine)


def _question_frame(report: AEOGEOReport) -> pd.DataFrame:
    readiness = {page.url: page.aeo.total for page in report.pages}
    return pd.DataFrame([{
        "Question": item.query, "Type": item.question_type.value.replace("_", " ").title(),
        "Mapped page": item.mapped_page or "NOT AVAILABLE", "Priority": item.priority_score,
        "Clicks": item.clicks, "Impressions": item.impressions,
        "GSC avg position": float(item.gsc_average_position) if item.gsc_average_position is not None else None,
        "Tracked SERP position": item.tracked_serp_position,
        "AEO readiness": readiness.get(item.mapped_page),
        "Evidence": " • ".join(item.evidence), "Recommended action": item.recommended_action,
    } for item in report.questions])


def _page_frame(report: AEOGEOReport, mode: str) -> pd.DataFrame:
    rows = []
    for page in report.pages:
        base = {"Page": page.url, "Score": getattr(page, mode).total, "Readiness": getattr(page, f"{mode}_level").value,
                "Structured data": ", ".join(page.structured_data_types) or "NOT OBSERVED",
                "Technical issues": "; ".join(page.technical_issues) or "None observed", "Recommendations": " • ".join(page.recommendations)}
        if mode == "aeo":
            base.update({"Question coverage": page.aeo.question_coverage, "Direct answer": page.aeo.direct_answer_structure,
                         "FAQ/schema": page.aeo.faq_schema, "Heading structure": page.aeo.heading_structure,
                         "Content clarity": page.aeo.content_clarity, "Technical accessibility": page.aeo.technical_accessibility})
        else:
            base.update({"Extractability": page.geo.extractability, "Entity clarity": page.geo.entity_clarity,
                         "Source support": page.geo.source_support, "Schema support": page.geo.structured_data,
                         "Topic clarity": page.geo.topic_clarity, "Technical accessibility": page.geo.technical_accessibility})
        rows.append(base)
    return pd.DataFrame(rows)


def render_aeo_geo(workflow=None) -> None:
    workflow = workflow or AEOGEODashboardWorkflow()
    st.subheader("AEO & GEO readiness")
    st.caption("Deterministic readiness analysis from persisted search, SERP, and crawl evidence.")
    st.warning("These are Nexora heuristic readiness scores. Actual AI answer visibility, citations, and model responses are not monitored.")
    st.session_state.setdefault("aeo_geo_report", None)
    try:
        targets = _run(workflow.targets())
    except Exception:
        targets = []
    if not targets:
        st.info("No persisted tracked-domain evidence is available. Add a keyword and crawl its site before loading readiness.")
        return
    with st.form("aeo-geo-load", border=True):
        target = st.selectbox("Target domain", targets)
        submitted = st.form_submit_button("Load readiness", type="primary")
    if submitted:
        try:
            st.session_state.aeo_geo_report = _run(workflow.analyze(target))
        except Exception:
            st.error("Persisted AEO/GEO readiness could not be loaded.")
    report = st.session_state.aeo_geo_report
    if not isinstance(report, AEOGEOReport):
        st.info("Load readiness explicitly. No crawler, Google API, rank provider, or AI provider runs on rerender.")
        return
    strong_aeo = sum(page.aeo_level.value == "STRONG" for page in report.pages)
    weak_aeo = sum(page.aeo_level.value == "WEAK" for page in report.pages)
    strong_geo = sum(page.geo_level.value == "STRONG" for page in report.pages)
    weak_geo = sum(page.geo_level.value == "WEAK" for page in report.pages)
    with st.container(horizontal=True):
        st.metric("Question opportunities", len(report.questions), border=True)
        st.metric("Strong AEO readiness", strong_aeo, border=True)
        st.metric("Weak AEO readiness", weak_aeo, border=True)
        st.metric("Strong GEO readiness", strong_geo, border=True)
        st.metric("Weak GEO readiness", weak_geo, border=True)
    question_frame = _question_frame(report)
    aeo_frame, geo_frame = _page_frame(report, "aeo"), _page_frame(report, "geo")
    question_tab, aeo_tab, geo_tab, detail_tab = st.tabs(["Question opportunities", "AEO pages", "GEO pages", "Page detail"])
    with question_tab:
        if question_frame.empty: st.info("No persisted question-form queries were identified.")
        else: st.dataframe(question_frame, hide_index=True, width="stretch", column_config={"Evidence": st.column_config.TextColumn(width="large"), "Recommended action": st.column_config.TextColumn(width="large")})
    with aeo_tab:
        if aeo_frame.empty: st.info("No compatible crawled pages have readiness evidence.")
        else: st.dataframe(aeo_frame, hide_index=True, width="stretch", column_config={"Score": st.column_config.ProgressColumn(min_value=0, max_value=100), "Recommendations": st.column_config.TextColumn(width="large")})
    with geo_tab:
        if geo_frame.empty: st.info("No compatible crawled pages have readiness evidence.")
        else: st.dataframe(geo_frame, hide_index=True, width="stretch", column_config={"Score": st.column_config.ProgressColumn(min_value=0, max_value=100), "Recommendations": st.column_config.TextColumn(width="large")})
    with detail_tab:
        if report.pages:
            selected = st.selectbox("Page", report.pages, format_func=lambda item: item.url)
            left, right = st.columns(2)
            left.metric("AEO readiness", f"{selected.aeo.total}/100", selected.aeo_level.value)
            right.metric("GEO readiness", f"{selected.geo.total}/100", selected.geo_level.value)
            st.markdown("**Observed evidence**")
            for item in selected.observations: st.write(f"- {item}")
            st.markdown("**Recommended actions**")
            for item in selected.recommendations: st.write(f"- {item}")
            st.caption("Content brief handoff: use a mapped question from this page in the existing Content briefs tab; its AEO/GEO sections use the same persisted evidence.")
        else:
            st.info("No page detail is available.")
    recommendations = pd.DataFrame([{"Page": page.url, "Recommendation": action} for page in report.pages for action in page.recommendations])
    with st.container(horizontal=True):
        st.download_button("Export questions CSV", question_frame.to_csv(index=False), "nexora_aeo_questions.csv", "text/csv")
        st.download_button("Export AEO CSV", aeo_frame.to_csv(index=False), "nexora_aeo_pages.csv", "text/csv")
        st.download_button("Export GEO CSV", geo_frame.to_csv(index=False), "nexora_geo_pages.csv", "text/csv")
        st.download_button("Export actions CSV", recommendations.to_csv(index=False), "nexora_aeo_geo_actions.csv", "text/csv")
        st.download_button("Export Markdown", AEOGEOService.markdown(report), "nexora_aeo_geo_readiness.md", "text/markdown")
