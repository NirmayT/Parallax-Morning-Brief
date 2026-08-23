"""Recall-oriented filtering for the advanced story-ranking pipeline.

Unlike the old version, this module does not discard repeated coverage. It
preserves distinct source paragraphs so story_ranker.py can cluster them and
use independent coverage as an importance signal.
"""
import config
import utils


def _paragraph_themes(paragraph):
    lowered = paragraph.lower()
    matched = set()
    for theme, keywords in config.MARKET_KEYWORDS.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            matched.add(theme)
    return matched


def _looks_promotional(paragraph):
    lowered = paragraph.lower()
    promo_terms = (
        "unsubscribe", "manage preferences", "view in browser", "privacy policy",
        "subscribe now", "limited-time offer", "sponsored by", "advertisement",
        "use code", "free trial", "upgrade your subscription",
    )
    return any(term in lowered for term in promo_terms)


def filter_and_categorize(records, reference_dt):
    by_theme = {theme: [] for theme in config.THEME_ORDER}
    sources = []
    exact_seen_by_source = set()
    exact_duplicates_removed = 0
    relevant_sources = set()
    total_retained = 0

    for record in records:
        source = record.get("sender_name", "Unknown source")
        subject = record.get("subject", "(no subject)")
        freshness = utils.freshness_tag(record.get("received"), reference_dt)
        source_retained = False

        for paragraph in record.get("paragraphs", []):
            paragraph = " ".join(str(paragraph).split())
            if not paragraph or _looks_promotional(paragraph):
                continue

            themes = _paragraph_themes(paragraph)
            if not themes:
                continue
            source_key = (
                source.lower().strip(),
                utils.normalize_headline(paragraph)[:180],
            )
            if source_key in exact_seen_by_source:
                exact_duplicates_removed += 1
                continue
            exact_seen_by_source.add(source_key)

            item = {
                "source": source,
                "subject": subject,
                "paragraph": paragraph,
                "freshness": freshness,
                "message_id": record.get("id"),
            }
            for theme in themes:
                by_theme.setdefault(theme, []).append(item)
            source_retained = True
            total_retained += 1

        if source_retained:
            relevant_sources.add(source)
            sources.append({
                "name": source,
                "subject": subject,
                "received": record.get("received"),
                "freshness": freshness,
                "id": record.get("id"),
            })

    by_theme = {theme: items for theme, items in by_theme.items() if items}
    return {
        "by_theme": by_theme,
        "sources": sources,
        "stats": {
            "total_records": len(records),
            "relevant_sources": len(relevant_sources),
            "retained_paragraphs": total_retained,
            "duplicates_removed": exact_duplicates_removed,
        },
    }
