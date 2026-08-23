"""Formatting, state, time and logging helpers."""
import os
from datetime import datetime, timedelta
import config


def safe_return(latest, previous):
    if latest is None or previous in (None, 0):
        return None
    return (latest - previous) / previous


def format_pct(value, decimals=1):
    return "n/a" if value is None else f"{value * 100:+.{decimals}f}%"


def format_level(value, decimals=2):
    return "n/a" if value is None else f"{value:,.{decimals}f}"


def format_rate(value, decimals=2):
    return "n/a" if value is None else f"{value:.{decimals}f}%"


def format_bps_change(latest, previous):
    if latest is None or previous is None:
        return "n/a"
    return f"{(latest - previous) * 100:+.0f} bp"


def now_local():
    return datetime.now(config.TIMEZONE)


def to_epoch(dt):
    return int(dt.timestamp())


def freshness_tag(received, reference):
    if received is None:
        return "unknown"
    hours = (reference - received).total_seconds() / 3600
    if hours <= 18:
        return "today"
    if hours <= 42:
        return "yesterday"
    return f"{max(2, int(hours // 24))} days ago"


def ensure_dirs():
    for directory in (config.STATE_DIR, config.OUTPUT_DIR, config.DEBUG_DIR):
        os.makedirs(directory, exist_ok=True)


def log(message):
    line = f"{now_local():%Y-%m-%d %H:%M:%S}  {message}"
    print(line)
    try:
        ensure_dirs()
        with open(config.LOG_FILE, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except Exception:
        pass


def read_last_run():
    try:
        with open(config.LAST_RUN_FILE, encoding="utf-8") as handle:
            value = datetime.fromisoformat(handle.read().strip())
        return value if value.tzinfo else value.replace(tzinfo=config.TIMEZONE)
    except Exception:
        return None


def write_last_run(value):
    ensure_dirs()
    with open(config.LAST_RUN_FILE, "w", encoding="utf-8") as handle:
        handle.write(value.isoformat())


def determine_fetch_start(reference):
    start = read_last_run() or reference - timedelta(hours=config.DEFAULT_FIRST_RUN_LOOKBACK_HOURS)
    return max(start, reference - timedelta(hours=config.MAX_LOOKBACK_HOURS))


def recently_ran(reference):
    previous = read_last_run()
    return bool(previous and (reference - previous).total_seconds() < config.MIN_HOURS_BETWEEN_RUNS * 3600)


def read_processed_ids():
    try:
        with open(config.PROCESSED_IDS_FILE, encoding="utf-8") as handle:
            return {line.strip() for line in handle if line.strip()}
    except Exception:
        return set()


def append_processed_ids(values):
    ensure_dirs()
    with open(config.PROCESSED_IDS_FILE, "a", encoding="utf-8") as handle:
        for value in values:
            handle.write(str(value) + "\n")


def normalize_headline(text):
    return " ".join("".join(char.lower() if char.isalnum() else " " for char in str(text)).split())
