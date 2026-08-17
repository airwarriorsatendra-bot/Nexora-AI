"""
==========================================================
NEXORA AI
Global Dashboard Styles
==========================================================
"""

from dashboard.config import *


def load_css():
    """
    Load global Streamlit CSS.
    """

    return f"""
<style>

/* -------------------------------------------------------
Main Layout
------------------------------------------------------- */

.main .block-container {{
    padding-top: 1rem;
    padding-bottom: 2rem;
    max-width: 100%;
}}

section.main {{
    background: #0B1120;
}}

body {{
    background: #0B1120;
    color: white;
}}

/* -------------------------------------------------------
Header
------------------------------------------------------- */

.nexora-title {{
    font-size: 42px;
    font-weight: 800;
    color: {PRIMARY_COLOR};
    margin-bottom: 0px;
}}

.nexora-subtitle {{
    font-size: 18px;
    color: #9CA3AF;
    margin-top: 0px;
    margin-bottom: 25px;
}}

/* -------------------------------------------------------
Metric Cards
------------------------------------------------------- */

div[data-testid="metric-container"] {{

    background: {CARD_BACKGROUND};

    border: 1px solid {CARD_BORDER};

    border-radius: 14px;

    padding: 20px;

    box-shadow: 0 10px 30px rgba(0,0,0,.20);

}}

div[data-testid="metric-container"] label {{

    color: #CBD5E1;

    font-size: 14px;

}}

div[data-testid="metric-container"] div {{

    color: white;

}}

/* -------------------------------------------------------
Cards
------------------------------------------------------- */

.nx-card {{

    background: {CARD_BACKGROUND};

    border: 1px solid {CARD_BORDER};

    border-radius: 16px;

    padding: 20px;

    margin-bottom: 18px;

    box-shadow: 0 10px 30px rgba(0,0,0,.25);

}}

.nx-card-title {{

    font-size: 20px;

    font-weight: 700;

    margin-bottom: 10px;

}}

.nx-card-text {{

    color: #CBD5E1;

    font-size: 15px;

    line-height: 1.7;

}}

/* -------------------------------------------------------
Sidebar
------------------------------------------------------- */

section[data-testid="stSidebar"] {{

    background: #111827;

}}

section[data-testid="stSidebar"] * {{

    color: white;

}}

section[data-testid="stSidebar"] hr {{

    border-color: #374151;

}}

/* -------------------------------------------------------
Buttons
------------------------------------------------------- */

.stButton>button {{

    width:100%;

    border-radius:12px;

    border:none;

    background:{PRIMARY_COLOR};

    color:white;

    font-weight:700;

    padding:12px;

    transition:0.3s;

}}

.stButton>button:hover {{

    background:#1D4ED8;

    transform:translateY(-2px);

}}

/* -------------------------------------------------------
Text Inputs
------------------------------------------------------- */

.stTextInput input {{

    border-radius:10px;

}}

.stTextArea textarea {{

    border-radius:10px;

}}

.stSelectbox div[data-baseweb="select"] {{

    border-radius:10px;

}}

.stMultiSelect div[data-baseweb="select"] {{

    border-radius:10px;

}}

/* -------------------------------------------------------
DataFrames
------------------------------------------------------- */

[data-testid="stDataFrame"] {{

    border-radius:14px;

    overflow:hidden;

    border:1px solid #374151;

}}

/* -------------------------------------------------------
Tabs
------------------------------------------------------- */

button[data-baseweb="tab"] {{

    font-weight:700;

}}

button[data-baseweb="tab"][aria-selected="true"] {{

    color:{PRIMARY_COLOR};

}}

/* -------------------------------------------------------
Expanders
------------------------------------------------------- */

.streamlit-expanderHeader {{

    font-weight:700;

}}

/* -------------------------------------------------------
Progress
------------------------------------------------------- */

.stProgress > div > div > div > div {{

    background:{PRIMARY_COLOR};

}}

/* -------------------------------------------------------
Success
------------------------------------------------------- */

.stAlert {{

    border-radius:12px;

}}

/* -------------------------------------------------------
Links
------------------------------------------------------- */

a {{

    color:#60A5FA;

}}

a:hover {{

    color:white;

}}

/* -------------------------------------------------------
Scrollbar
------------------------------------------------------- */

::-webkit-scrollbar {{

    width:10px;

}}

::-webkit-scrollbar-track {{

    background:#111827;

}}

::-webkit-scrollbar-thumb {{

    background:#374151;

    border-radius:10px;

}}

::-webkit-scrollbar-thumb:hover {{

    background:#4B5563;

}}

</style>
"""


def apply_styles(st):
    """
    Apply CSS to Streamlit.
    """

    st.markdown(
        load_css(),
        unsafe_allow_html=True,
    )


def page_header(st, title, subtitle=""):
    """
    Render page title.
    """

    st.markdown(
        f"""
<div class="nexora-title">
{title}
</div>

<div class="nexora-subtitle">
{subtitle}
</div>
""",
        unsafe_allow_html=True,
    )


def card(st, title, body):
    """
    Render reusable dashboard card.
    """

    st.markdown(
        f"""
<div class="nx-card">

<div class="nx-card-title">
{title}
</div>

<div class="nx-card-text">
{body}
</div>

</div>
""",
        unsafe_allow_html=True,
    )