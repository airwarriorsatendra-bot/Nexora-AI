"""Safe configuration status center; secrets are never displayed."""

from __future__ import annotations

import os
import streamlit as st


def _provider_card(name: str, variable: str) -> None:
    with st.container(border=True):
        st.markdown(f"**{name}**")
        st.caption("Configured" if os.getenv(variable) else "Not configured")


def render_settings(st) -> None:
    st.subheader("Settings")
    st.caption("Safe configuration status for this local workspace. Secret values are never shown.")
    st.subheader("AI providers")
    with st.container(horizontal=True):
        for name, variable in (("NVIDIA", "NVIDIA_API_KEY"), ("Groq", "GROQ_API_KEY"), ("OpenAI", "OPENAI_API_KEY"), ("Gemini", "GOOGLE_API_KEY"), ("Claude", "ANTHROPIC_API_KEY")):
            _provider_card(name, variable)
    st.subheader("Search providers")
    with st.container(horizontal=True):
        for name, variable in (("Tavily", "TAVILY_API_KEY"), ("Serper", "SERPER_API_KEY"), ("Brave", "BRAVE_API_KEY"), ("Google CSE", "GOOGLE_CSE_API_KEY"), ("Perplexity", "PERPLEXITY_API_KEY")):
            _provider_card(name, variable)
    st.subheader("Google data sources")
    with st.container(horizontal=True):
        _provider_card("Google Search Console", "GSC_REFRESH_TOKEN")
        _provider_card("Google Analytics 4", "GA4_PROPERTY_ID")
    st.subheader("Application and database")
    with st.container(horizontal=True):
        st.metric("Application", "Nexora AI", border=True)
        st.metric("Operator", "Nexora Digital Hub", border=True)
        st.metric("Database", "SQLite", border=True)
        st.metric("Delivery mode", "Dry run", border=True)
    if st.button("Clear local session", type="secondary"):
        st.session_state.clear()
        st.rerun()
