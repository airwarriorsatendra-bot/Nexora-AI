"""
==========================================================
NEXORA AI
Settings
==========================================================
"""

import os
import streamlit as st


def render_settings(st):
    """
    Render application settings page.
    """

    st.subheader("⚙ Settings")

    st.markdown("### API Configuration")

    groq = os.getenv("GROQ_API_KEY", "")
    serper = os.getenv("SERPER_API_KEY", "")

    st.text_input(
        "Groq API Key",
        value="Configured" if groq else "",
        disabled=True,
        placeholder="Not configured",
    )

    st.text_input(
        "Serper API Key",
        value="Configured" if serper else "",
        disabled=True,
        placeholder="Not configured",
    )

    st.divider()

    st.markdown("### Database")

    st.success("SQLite Database Connected")

    st.divider()

    st.markdown("### Application")

    st.write("**Application:** Nexora AI")
    st.write("**Version:** 1.0.0")
    st.write("**Status:** Running")

    st.divider()

    if st.button("Clear Session"):

        st.session_state.clear()

        st.success("Session cleared successfully.")