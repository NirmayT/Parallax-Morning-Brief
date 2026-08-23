import os
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("America/Toronto")
GMAIL_LABEL = "PRG-Market-Newsletters"
DEFAULT_FIRST_RUN_LOOKBACK_HOURS = 24
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

# Configure these two values for your accounts.
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "").strip()
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "").strip()
EMAIL_SUBJECT_PREFIX = "Parallax"

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
ENABLE_AI_BORDERLINE_ADJUDICATION = False
AI_MAX_TOKENS = 6500
MAX_EXTRACTION_FALLBACK_SHARE = 0.25
AI_MAX_HEADLINES = 4

# Personal prototype disclosure.
PROJECT_DISCLAIMER = "Personal project. Not affiliated with or endorsed by any employer."