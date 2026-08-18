"""Premium Site Crawl workspace; crawling occurs only on explicit submission."""
from __future__ import annotations

import asyncio
import pandas as pd
import streamlit as st

from dashboard.site_crawl_workflow import SiteCrawlDashboardWorkflow


def _run(coro): return asyncio.run(coro)


def _pages(crawl):
    return pd.DataFrame([{"URL":p.normalized_url,"Status":p.status_code,"Indexability signal":p.indexability.value,"Title":p.title,"H1":p.h1s[0] if p.h1s else "","Words":p.word_count,"Inlinks":p.inlink_count,"Outlinks":p.outlink_count,"Depth":p.depth,"Canonical":p.canonical or "","Issues":"; ".join(p.issues)} for p in crawl.pages])


def _issues(crawl): return pd.DataFrame([i.model_dump(mode="json") for i in crawl.issues])
def _links(crawl): return pd.DataFrame([{"Source":l.source_url,"Anchor":l.anchor_text,"Target":l.target_url,"Target status":l.target_status,"Nofollow":l.nofollow,"Issue":l.issue or ""} for l in crawl.links])
def _opportunities(crawl): return pd.DataFrame([{"Priority":o.priority,"Target page":o.target_url,"Evidence":" • ".join(o.evidence),"Suggested action":o.suggested_action,"Provenance":" + ".join(o.provenance)} for o in crawl.opportunities])


def render_site_crawl(workflow=None):
    workflow = workflow or SiteCrawlDashboardWorkflow(); st.session_state.setdefault("site_crawl_result", None)
    st.caption("Bounded same-site technical crawl. Signals are observations, not Google index status or ranking factors.")
    with st.form("site-crawl-controls", border=True):
        start_url = st.text_input("Start URL", placeholder="https://example.com/")
        with st.container(horizontal=True):
            max_pages = st.number_input("Max pages", 1, 500, 100); max_depth = st.number_input("Max depth", 0, 10, 4); concurrency = st.number_input("Concurrency", 1, 10, 4)
        submitted = st.form_submit_button("Run crawl", type="primary")
    if submitted:
        try:
            with st.status("Running bounded crawl…", expanded=True) as status:
                st.session_state.site_crawl_result = _run(workflow.run(start_url, int(max_pages), int(max_depth), int(concurrency)))
                status.update(label="Crawl completed", state="complete")
        except Exception: st.error("The bounded site crawl could not be completed.")
    crawl = st.session_state.site_crawl_result
    if crawl is None:
        try: crawl = _run(workflow.latest())
        except Exception: crawl = None
    if crawl is None:
        st.info("Run a crawl or load persisted crawl history. No external request occurs on rerender."); return
    stats = crawl.summary.statistics
    with st.container(horizontal=True):
        st.metric("Pages crawled", stats.pages_crawled, border=True); st.metric("Indexable signals", stats.indexable_signals, border=True); st.metric("Broken links", stats.broken_links, border=True); st.metric("Redirects", stats.redirects, border=True); st.metric("Internal links", stats.internal_links, border=True)
    with st.container(horizontal=True):
        st.metric("No crawled inlinks", stats.no_crawled_inlinks, border=True); st.metric("Depth 4+", stats.depth_four_plus, border=True); st.metric("Duplicate titles", stats.duplicate_titles, border=True); st.metric("Missing meta", stats.missing_meta, border=True); st.metric("Technical site score", f"{crawl.summary.overall_score:.0f}", border=True)
    st.caption(crawl.summary.disclaimer + " Robots.txt enforcement: not supported in this implementation.")
    overview, technical, pages_tab, links_tab, opportunity_tab, history_tab = st.tabs(["Overview","Technical issues","Pages","Internal links","Link opportunities","Crawl history"])
    pages, issues, links, opportunities = _pages(crawl), _issues(crawl), _links(crawl), _opportunities(crawl)
    with overview:
        scores = pd.DataFrame(crawl.summary.category_scores.items(), columns=["Category","Score"]); st.bar_chart(scores, x="Category", y="Score", horizontal=True, color="#5B7CFF", height=280)
    with technical:
        st.dataframe(issues, hide_index=True, width="stretch"); st.download_button("Export issues CSV", issues.to_csv(index=False), "nexora_site_crawl_issues.csv", "text/csv")
    with pages_tab:
        st.dataframe(pages, hide_index=True, width="stretch", column_config={"URL":st.column_config.TextColumn(width="large"),"Title":st.column_config.TextColumn(width="large")}); st.download_button("Export pages CSV", pages.to_csv(index=False), "nexora_site_crawl_pages.csv", "text/csv")
    with links_tab:
        st.dataframe(links, hide_index=True, width="stretch"); st.download_button("Export internal links CSV", links.to_csv(index=False), "nexora_site_crawl_links.csv", "text/csv")
    with opportunity_tab:
        if opportunities.empty: st.info("No deterministic internal-link opportunities were identified.")
        else: st.dataframe(opportunities, hide_index=True, width="stretch")
        st.download_button("Export link opportunities CSV", opportunities.to_csv(index=False), "nexora_link_opportunities.csv", "text/csv")
    with history_tab:
        history = _run(workflow.history()); frame = pd.DataFrame([{"Completed":c.completed_at,"Start URL":str(c.request.start_url),"Pages":len(c.pages),"Score":c.summary.overall_score,"Crawl ID":str(c.crawl_id)} for c in history]); st.dataframe(frame, hide_index=True, width="stretch")
        comparison = _run(workflow.comparison(crawl)); comparison_frame = pd.DataFrame([{"Change type":kind,"Value":value} for kind,values in (("New page",comparison.new_pages),("Missing page candidate",comparison.missing_pages),("New issue",comparison.new_issues),("Resolved issue",comparison.resolved_issues),("Status change",comparison.status_changes),("Metadata change",comparison.metadata_changes),("Inlink change",comparison.inlink_changes),("Depth change",comparison.depth_changes)) for value in values]); st.download_button("Export crawl comparison CSV", comparison_frame.to_csv(index=False), "nexora_crawl_comparison.csv", "text/csv")

