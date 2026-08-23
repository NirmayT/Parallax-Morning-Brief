"""Short-lived memory of published cluster headlines, not raw newsletter bodies."""
import json
import os
from datetime import timedelta
import config
import utils


def load_recent(reference):
    cutoff = reference.date() - timedelta(days=config.STORY_MEMORY_DAYS)
    rows, keys = [], set()
    try:
        with open(config.STORY_MEMORY_FILE, encoding="utf-8") as handle:
            for line in handle:
                item = json.loads(line)
                if __import__("datetime").date.fromisoformat(item["date"]) >= cutoff:
                    rows.append(f"- {item['headline']} (covered {item['date']})")
                    keys.add(utils.normalize_headline(item["headline"]))
    except Exception:
        pass
    return "\n".join(rows[-20:]) or "None.", keys


def remember(headlines, reference):
    utils.ensure_dirs()
    with open(config.STORY_MEMORY_FILE, "a", encoding="utf-8") as handle:
        for item in headlines:
            headline = item.get("headline", "").strip()
            if headline:
                handle.write(json.dumps({"date": reference.date().isoformat(), "headline": headline}) + "\n")
