"""Central premium visual system for Nexora's Streamlit presentation layer."""

from __future__ import annotations


def load_css() -> str:
    return """
<style>
:root { color-scheme: dark; }
section.main, body { background:#080B12; color:#F8FAFC; }
.main .block-container { max-width:1440px; padding:1.5rem 2rem 2.5rem; }
section[data-testid="stSidebar"] { background:#0D111C; border-right:1px solid #252C3B; }
section[data-testid="stSidebar"] [data-baseweb="select"] { background:#171D2B; border-radius:10px; }
.nexora-title { font-size:34px; font-weight:700; letter-spacing:-.03em; margin:0; color:#F8FAFC; }
.nexora-subtitle { font-size:15px; color:#94A3B8; margin:.35rem 0 1.5rem; }
div[data-testid="metric-container"] { background:#111622; border:1px solid #252C3B; border-radius:14px; padding:1rem; box-shadow:none; }
div[data-testid="metric-container"] label { color:#94A3B8; font-size:.8rem; text-transform:uppercase; letter-spacing:.06em; }
div[data-testid="metric-container"] [data-testid="stMetricValue"] { color:#F8FAFC; }
.stButton > button { border-radius:10px; border:1px solid #5B7CFF; background:#5B7CFF; color:#FFF; font-weight:600; min-height:2.6rem; }
.stButton > button:hover { background:#4969EA; border-color:#4969EA; }
.stTextInput input, .stTextArea textarea, [data-baseweb="select"] { background:#111622; border-color:#252C3B; border-radius:10px; }
[data-testid="stDataFrame"] { border:1px solid #252C3B; border-radius:12px; overflow:hidden; }
[data-testid="stAlert"] { border-radius:10px; border-color:#252C3B; }
[data-testid="stExpander"] { border:1px solid #252C3B; border-radius:10px; background:#111622; }
button[data-baseweb="tab"] { font-weight:600; color:#94A3B8; }
button[data-baseweb="tab"][aria-selected="true"] { color:#5B7CFF; }
</style>
"""


def apply_styles(st) -> None:
    st.markdown(load_css(), unsafe_allow_html=True)


def page_header(st, title: str, subtitle: str = "") -> None:
    st.markdown(f'<div class="nexora-title">{title}</div><div class="nexora-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def card(st, title: str, body: str) -> None:
    with st.container(border=True):
        st.subheader(title)
        st.caption(body)
