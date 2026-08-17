"""
==========================================================
NEXORA AI
Configuration
==========================================================
"""

from pathlib import Path
import os

# ---------------------------------------------------------
# Project Root
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------
# Storage
# ---------------------------------------------------------

STORAGE_DIR = PROJECT_ROOT / "storage"

DATABASE_FILE = STORAGE_DIR / "backlinks.db"

OUTREACH_DATABASE = STORAGE_DIR / "outreach.db"

LOG_DIRECTORY = STORAGE_DIR / "logs"

EXPORT_DIRECTORY = STORAGE_DIR / "exports"

REPORT_DIRECTORY = STORAGE_DIR / "reports"

CACHE_DIRECTORY = STORAGE_DIR / "cache"

# ---------------------------------------------------------
# Create Missing Directories
# ---------------------------------------------------------

for directory in [
    STORAGE_DIR,
    LOG_DIRECTORY,
    EXPORT_DIRECTORY,
    REPORT_DIRECTORY,
    CACHE_DIRECTORY,
]:
    directory.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------
# Application
# ---------------------------------------------------------

APP_NAME = "Nexora AI"

APP_VERSION = "1.0.0"

APP_DESCRIPTION = (
    "AI Powered Digital Marketing Operating System"
)

PAGE_TITLE = "Nexora AI"

PAGE_ICON = "🚀"

LAYOUT = "wide"

SIDEBAR_STATE = "expanded"

# ---------------------------------------------------------
# Theme
# ---------------------------------------------------------

PRIMARY_COLOR = "#2563EB"

SECONDARY_COLOR = "#0F172A"

SUCCESS_COLOR = "#10B981"

WARNING_COLOR = "#F59E0B"

ERROR_COLOR = "#EF4444"

CARD_BACKGROUND = "#111827"

CARD_BORDER = "#374151"

TEXT_PRIMARY = "#FFFFFF"

TEXT_SECONDARY = "#9CA3AF"

# ---------------------------------------------------------
# API Keys
# ---------------------------------------------------------

SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# ---------------------------------------------------------
# Dashboard
# ---------------------------------------------------------

ROWS_PER_PAGE = 25

MAX_EXPORT_ROWS = 100000

DEFAULT_AI_SCORE = 70

MAX_SEARCH_RESULTS = 100

# ---------------------------------------------------------
# Website Crawler
# ---------------------------------------------------------

CRAWLER_TIMEOUT = 8

CRAWLER_RETRIES = 2

MAX_WORKERS = 8

USER_AGENT = (
    "Mozilla/5.0 "
    "(Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/138.0 Safari/537.36"
)

# ---------------------------------------------------------
# Outreach
# ---------------------------------------------------------

EMAIL_HISTORY_LIMIT = 500

DEFAULT_EMAIL_MODEL = "llama-3.3-70b-versatile"

# ---------------------------------------------------------
# Reports
# ---------------------------------------------------------

EXPORT_FILENAME = "nexora_prospects.csv"

PDF_REPORT_NAME = "nexora_report.pdf"

EXCEL_REPORT_NAME = "nexora_report.xlsx"

# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------

LOG_LEVEL = "INFO"

LOG_FILE = LOG_DIRECTORY / "nexora.log"

# ---------------------------------------------------------
# Supported Industries
# ---------------------------------------------------------

SUPPORTED_INDUSTRIES = [

    "Fashion",

    "Health",

    "Real Estate",

    "Automobile",

    "Education",

    "Finance",

    "Insurance",

    "Travel",

    "Hospitality",

    "Restaurants",

    "Technology",

    "SaaS",

    "E-commerce",

    "Manufacturing",

    "Legal",

    "Construction",

    "Local Business",

    "Beauty",

    "Fitness",

    "Digital Marketing",

    "Agency",

    "Healthcare",

    "NGO",

    "Other",

]

# ---------------------------------------------------------
# Status
# ---------------------------------------------------------

STATUS_COLORS = {

    "New": "#2563EB",

    "Contacted": "#10B981",

    "Pending": "#F59E0B",

    "Rejected": "#EF4444",

    "Completed": "#14B8A6",

}