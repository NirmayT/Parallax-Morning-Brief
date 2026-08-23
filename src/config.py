import os
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("America/Toronto")
GMAIL_LABEL = "PRG-Market-Newsletters"
DEFAULT_FIRST_RUN_LOOKBACK_HOURS = 48
MAX_LOOKBACK_HOURS = 72
MIN_HOURS_BETWEEN_RUNS = 1
MAX_PARAGRAPHS_PER_SOURCE = 10
MAX_CHARS_PER_PARAGRAPH = 750
STORY_EXTRACTION_BATCH_SIZE = 4

EQUITY_TICKERS = {
    "S&P 500": "^GSPC",
    "Nasdaq 100": "^NDX",
    "S&P/TSX Composite": "^GSPTSE",
}

# Market-standard quote conventions. A rise in USD/CNY means USD strengthened.
FX_PAIRS = {
    "EUR/USD": {"symbol": "EURUSD=X", "base": "EUR", "quote": "USD", "decimals": 4},
    "USD/CNY": {"symbol": "CNY=X", "base": "USD", "quote": "CNY", "decimals": 4},
    "USD/CAD": {"symbol": "USDCAD=X", "base": "USD", "quote": "CAD", "decimals": 4},
    "USD/JPY": {"symbol": "USDJPY=X", "base": "USD", "quote": "JPY", "decimals": 2},
}

# ^IRX is the 13-week Treasury bill; the others are Treasury yield indices.
RATE_TICKERS = {
    "US 3M": "^IRX",
    "US 5Y": "^FVX",
    "US 10Y": "^TNX",
    "US 30Y": "^TYX",
}
OVERNIGHT_RATES = {"SOFR": None, "CORRA": None}

MARKET_KEYWORDS = {
    "Rates and Central Banks": [
        "federal reserve", "fed", "fomc", "bank of canada", "boc", "ecb",
        "interest rate", "rate cut", "rate hike", "treasury", "yield", "bond",
        "central bank", "debt issuance", "liquidity",
    ],
    "Macro and Economics": [
        "inflation", "cpi", "pce", "employment", "jobs", "payrolls",
        "unemployment", "growth", "gdp", "consumer spending", "retail sales",
        "fiscal", "deficit", "productivity", "housing", "manufacturing", "services",
    ],
    "Foreign Exchange": [
        "dollar", "currency", "fx", "foreign exchange", "cad", "loonie", "euro",
        "yen", "yuan", "renminbi", "sterling", "pound", "eur/usd", "usd/cny",
        "usd/cad", "usd/jpy",
    ],
    "Equities and Credit": [
        "equity", "equities", "stock", "stocks", "s&p", "nasdaq", "tsx",
        "earnings", "credit", "spread", "banks", "financials", "shares",
    ],
    "Commodities": [
        "oil", "crude", "brent", "wti", "gold", "silver", "natural gas",
        "copper", "commodity", "commodities",
    ],
    "Volatility and Risk": [
        "volatility", "vix", "risk-off", "risk-on", "selloff", "rally",
        "sentiment", "safe haven", "flight to safety",
    ],
}
THEME_ORDER = [
    "Rates and Central Banks", "Macro and Economics", "Foreign Exchange",
    "Equities and Credit", "Commodities", "Volatility and Risk",
]

# Known sources affect metadata and specialist protection, not factual truth.
# NOTE: this dict is not currently read anywhere in the pipeline -- the live
# classification that actually drives scoring is SPECIALIST_MARKERS in
# story_ranker.py. Keep this in sync with that tuple manually until the two
# are unified; it exists for human reference and any future wiring-in.
SOURCE_PROFILES = {
    "Axios Markets": {"type": "general", "quality_weight": 1.0},
    "Yahoo Finance Morning Brief": {"type": "general", "quality_weight": 1.0},
    "Reuters Morning Bid": {"type": "general", "quality_weight": 1.0},
    "Off the Charts": {"type": "specialist", "quality_weight": 1.05},
    "Apollo": {"type": "specialist", "quality_weight": 1.05},  # publishes as "The Daily Spark" -- same source, one entry
    "Orange Juice Newsletter": {"type": "specialist", "quality_weight": 1.05},  # FXStreet, FX-focused
}

TARGET_SELECTED_STORIES = 3
MAX_SELECTED_STORIES = 3
MIN_SELECTED_STORIES = 2 
MAX_STORIES_PER_THEME = 2
MIN_CONSENSUS_SOURCES = 2
ALLOW_SPECIALIST_EXCEPTION = True

# Delivery/runtime configuration. Real values live only in environment variables.
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "").strip()  # optional reply-to address
EMAIL_SUBJECT_PREFIX = "Parallax"

# Subscriber database (server-side only).
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SECRET_KEY = (
    os.getenv("SUPABASE_SECRET_KEY", "").strip()
    or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()  # legacy fallback
)

# Exact-HTML broadcast delivery via Resend.
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "").strip()
RESEND_REPLY_TO = os.getenv("RESEND_REPLY_TO", SENDER_EMAIL).strip()
PUBLIC_SITE_URL = os.getenv(
    "PUBLIC_SITE_URL",
    "https://parallax-research-plum.vercel.app",
).rstrip("/")

# Safety cap for one production broadcast. Keep this <= your provider/day limit.
BROADCAST_MAX_RECIPIENTS = int(os.getenv("BROADCAST_MAX_RECIPIENTS", "90"))

STATE_DIR = "state"
LAST_RUN_FILE = "state/last_run.txt"
PROCESSED_IDS_FILE = "state/processed_ids.txt"
STORY_MEMORY_FILE = "state/seen_stories.jsonl"
OUTPUT_DIR = "outputs"
DEBUG_DIR = "debug"
LOG_FILE = "outputs/run_log.txt"
STORY_MEMORY_DAYS = 4

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]
GMAIL_SEND_SCOPES = GMAIL_SCOPES
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

AI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
AI_MODEL = "gemini-3.6-flash"
AI_API_KEY_ENV = "GEMINI_API_KEY"
AI_TEMPERATURE = 0.4
AI_REASONING_EFFORT = "low"
# Free-tier safety: deterministic clustering is strong enough for v1.0 and
# skipping the optional SAME/DIFFERENT call leaves headroom for the final editor.
ENABLE_AI_BORDERLINE_ADJUDICATION = False
AI_MAX_TOKENS = 6500
MAX_EXTRACTION_FALLBACK_SHARE = 0.25
AI_MAX_HEADLINES = 4

# Personal prototype disclosure.
PROJECT_DISCLAIMER = "Personal project. Not affiliated with or endorsed by any employer."