"""Parallax story extraction, clustering, scoring, and editorial selection.

Gemini is used only for short labeled-text tasks. Python owns every data
structure. No ranking-stage call asks Gemini to return JSON.
"""
from __future__ import annotations

import os
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from difflib import SequenceMatcher
from typing import Any

import config
import utils

try:
    from openai import OpenAI
    OPENAI_SDK_AVAILABLE = True
except Exception:
    OPENAI_SDK_AVAILABLE = False

TARGET_SELECTED_STORIES = getattr(config, "TARGET_SELECTED_STORIES", 3)
MAX_SELECTED_STORIES = getattr(config, "MAX_SELECTED_STORIES", 4)
MIN_SELECTED_STORIES = getattr(config, "MIN_SELECTED_STORIES", 2)
MAX_STORIES_PER_THEME = getattr(config, "MAX_STORIES_PER_THEME", 2)
MIN_CONSENSUS_SOURCES = getattr(config, "MIN_CONSENSUS_SOURCES", 2)
ALLOW_SPECIALIST_EXCEPTION = getattr(config, "ALLOW_SPECIALIST_EXCEPTION", True)
STORY_EXTRACTION_BATCH_SIZE = getattr(config, "STORY_EXTRACTION_BATCH_SIZE", 5)
ENABLE_AI_BORDERLINE_ADJUDICATION = getattr(config, "ENABLE_AI_BORDERLINE_ADJUDICATION", True)
MAX_EXTRACTION_FALLBACK_SHARE = getattr(config, "MAX_EXTRACTION_FALLBACK_SHARE", 0.25)
AI_MIN_CALL_INTERVAL_SECONDS = getattr(config, "AI_MIN_CALL_INTERVAL_SECONDS", 13.0)
AI_MAX_RATE_LIMIT_RETRIES = getattr(config, "AI_MAX_RATE_LIMIT_RETRIES", 3)


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "have", "in", "is", "it", "its", "of", "on", "or", "that", "the", "this",
    "to", "was", "were", "will", "with", "after", "ahead", "about", "amid",
}
ALIASES = {
    "fed": "federal_reserve", "fomc": "federal_reserve",
    "cuts": "cut", "reductions": "cut", "reduction": "cut",
    "hikes": "hike", "rates": "rate", "yields": "yield",
    "stocks": "stock", "equities": "equity", "treasuries": "treasury",
    "expectations": "expectation", "markets": "market", "investors": "investor",
}
ASSET_KEYWORDS = {
    "equities": ("stock", "equity", "s&p", "nasdaq", "tsx", "earnings", "shares"),
    "fx": ("fx", "dollar", "euro", "yen", "yuan", "loonie", "currency", "eur/usd", "usd/cny", "usd/cad", "usd/jpy"),
    "rates": ("treasury", "yield", "bond", "fed", "federal reserve", "rate cut", "central bank"),
    "commodities": ("oil", "gold", "silver", "copper", "commodity", "brent", "wti"),
    "macro": ("inflation", "cpi", "pce", "jobs", "payrolls", "employment", "gdp", "growth", "retail sales", "fiscal", "deficit", "housing"),
}
SPECIALIST_MARKERS = ("apollo", "daily spark", "off the charts", "orange juice")

# Hard editorial hygiene. These are operational/promotional phrases, not market developments.
NON_EDITORIAL_PHRASES = (
    "unsubscribe", "email preferences", "subscription management", "manage subscription",
    "privacy team", "privacy policy", "customer support", "cashback", "cash back",
    "rebate on trades", "trading cashback", "broker services", "broker service",
    "refer a friend", "promotional offer", "promotional", "advertisement",
)
ALLOWED_ASSETS = {"equities", "fx", "rates", "commodities", "macro"}


@dataclass
class Story:
    story_id: str
    headline: str
    summary: str
    evidence: str
    source: str
    freshness: str
    themes: list[str] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    catalyst: str = ""
    has_supported_number: bool = False
    extraction_method: str = "fallback"
    editorial: bool = True


@dataclass
class Cluster:
    cluster_id: str
    canonical_story: str
    summary: str
    evidence: list[str]
    sources: list[str]
    themes: list[str]
    assets: list[str]
    entities: list[str]
    catalysts: list[str]
    freshness_labels: list[str]
    member_story_ids: list[str]
    extraction_methods: list[str]
    score: float = 0.0
    score_breakdown: dict[str, float] = field(default_factory=dict)
    specialist_exception: bool = False


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("—", ", ").replace("–", ", ")).strip()


def _tokens(text: str) -> set[str]:
    output = set()
    for word in re.findall(r"[a-z0-9]+(?:/[a-z0-9]+)?", _clean(text).lower()):
        if word in STOPWORDS or len(word) < 2:
            continue
        word = ALIASES.get(word, word)
        if word.endswith("s") and len(word) > 4 and word != "basis":
            word = word[:-1]
        output.add(word)
    return output


def _jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right) if left and right else 0.0


def _infer_assets(text: str) -> list[str]:
    lower = _clean(text).lower()
    return [asset for asset, words in ASSET_KEYWORDS.items() if any(word in lower for word in words)]


def _client():
    if not OPENAI_SDK_AVAILABLE:
        return None
    key = os.environ.get(config.AI_API_KEY_ENV, "").strip()
    return None if not key else OpenAI(api_key=key, base_url=config.AI_BASE_URL)


def _daily_quota_exhausted(message: str) -> bool:
    text = str(message or "")
    lower = text.lower()
    return (
        "GenerateRequestsPerDayPerProjectPerModel-FreeTier" in text
        or "requests_per_day" in lower
        or "requests per day" in lower
        or "perdayperprojectpermodel" in lower
    )


def _text_call(client, system: str, user: str, max_tokens=1200, temperature=0.05) -> str:
    """Make one paced Gemini/OpenAI-compatible text request.

    Ranking and synthesis share one process-wide pacing clock via config.
    Temporary RPM limits receive bounded retries. A daily free-tier quota
    exhaustion fails immediately and disables further AI calls for this run.
    """
    if getattr(config, "_AI_DAILY_QUOTA_EXHAUSTED", False):
        raise RuntimeError("Gemini daily free-tier request quota exhausted.")

    kwargs = {
        "model": config.AI_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    reasoning_effort = getattr(config, "AI_REASONING_EFFORT", "low")
    if reasoning_effort:
        kwargs["reasoning_effort"] = reasoning_effort

    response = None

    for attempt in range(AI_MAX_RATE_LIMIT_RETRIES + 1):
        last_call = getattr(config, "_AI_LAST_CALL_TIME", 0.0)
        elapsed = (
            time.monotonic() - last_call
            if last_call
            else AI_MIN_CALL_INTERVAL_SECONDS
        )

        if last_call and elapsed < AI_MIN_CALL_INTERVAL_SECONDS:
            wait = AI_MIN_CALL_INTERVAL_SECONDS - elapsed
            utils.log(f"[AI] Rate-limit pacing: waiting {wait:.1f}s.")
            time.sleep(wait)

        if getattr(config, "_AI_DAILY_QUOTA_EXHAUSTED", False):
            raise RuntimeError("Gemini daily free-tier request quota exhausted.")

        try:
            config._AI_LAST_CALL_TIME = time.monotonic()
            response = client.chat.completions.create(**kwargs)
            break

        except Exception as exc:
            error_text = str(exc)

            if _daily_quota_exhausted(error_text):
                config._AI_DAILY_QUOTA_EXHAUSTED = True
                raise RuntimeError(
                    "Gemini daily free-tier request quota exhausted."
                ) from exc

            is_rate_limit = (
                "429" in error_text
                or "RESOURCE_EXHAUSTED" in error_text
                or "rate limit" in error_text.lower()
                or "quota exceeded" in error_text.lower()
            )

            if not is_rate_limit or attempt >= AI_MAX_RATE_LIMIT_RETRIES:
                raise

            retry_match = re.search(
                r"retry in\s+([0-9.]+)s",
                error_text,
                flags=re.IGNORECASE,
            )
            if not retry_match:
                retry_match = re.search(
                    r"retryDelay['\"]?\s*:\s*['\"]([0-9.]+)s",
                    error_text,
                    flags=re.IGNORECASE,
                )

            server_wait = float(retry_match.group(1)) if retry_match else 15.0
            wait = max(server_wait + 2.0, AI_MIN_CALL_INTERVAL_SECONDS)

            utils.log(
                "[AI] Gemini temporary rate limit reached; "
                f"waiting {wait:.1f}s before retry "
                f"{attempt + 1}/{AI_MAX_RATE_LIMIT_RETRIES}."
            )
            time.sleep(wait)

    if response is None:
        raise RuntimeError("AI request failed without returning a response.")

    choice = response.choices[0]
    text = (choice.message.content or "").strip()
    usage = getattr(response, "usage", None)
    finish_reason = getattr(choice, "finish_reason", None)

    utils.log(
        "[AI] "
        f"finish_reason={finish_reason} "
        f"prompt_tokens={getattr(usage, 'prompt_tokens', None)} "
        f"completion_tokens={getattr(usage, 'completion_tokens', None)} "
        f"chars={len(text)}"
    )

    if not text:
        raise RuntimeError("AI returned empty content")
    if str(finish_reason).lower() == "length":
        raise RuntimeError(
            "AI response truncated because output token limit was reached"
        )

    return text


def _flatten(newsletters: dict) -> list[dict]:
    items, seen = [], set()
    for theme in config.THEME_ORDER:
        for item in newsletters.get("by_theme", {}).get(theme, []):
            key = (_clean(item.get("source")).lower(), _clean(item.get("paragraph")).lower())
            if key in seen:
                continue
            seen.add(key)
            items.append({
                "input_id": f"N{len(items)+1}", "source": item.get("source", "Unknown"),
                "subject": item.get("subject", ""), "paragraph": _clean(item.get("paragraph")),
                "freshness": item.get("freshness", "unknown"), "theme_hint": theme,
            })
    return items


def _looks_non_editorial(headline: str, summary: str, evidence: str) -> bool:
    text = _clean(" ".join([headline, summary, evidence])).lower()
    return any(phrase in text for phrase in NON_EDITORIAL_PHRASES)


def _is_editorial_story(story: Story) -> bool:
    if not story.editorial:
        return False
    if _looks_non_editorial(story.headline, story.summary, story.evidence):
        return False
    assets = {a for a in story.assets if a in ALLOWED_ASSETS}
    return bool(assets)


def _fallback_story(item: dict, index=1) -> Story:
    text = _clean(item.get("paragraph"))
    subject = _clean(item.get("subject"))
    headline = subject if subject and subject != "(no subject)" else text[:90]
    assets = _infer_assets(headline + " " + text)
    editorial = bool(assets) and not _looks_non_editorial(headline, text, text)
    return Story(
        f"{item['input_id']}_S{index}", headline, text, text,
        item.get("source", "Unknown"), item.get("freshness", "unknown"),
        [_clean(item.get("theme_hint")).lower()], assets,
        [], "", bool(re.search(r"\d", text)), "paragraph_fallback", editorial,
    )


def _field(block: str, name: str) -> str:
    match = re.search(rf"(?im)^\s*{re.escape(name)}\s*:\s*(.+?)\s*$", block)
    return _clean(match.group(1)) if match else ""


def _parse_story_blocks(text: str, batch: list[dict]) -> list[Story]:
    """Parse forgiving labeled blocks. Invalid blocks are skipped, not fatal."""
    by_id = {item["input_id"]: item for item in batch}
    blocks = re.split(r"(?im)^\s*STORY\s*$", text)
    stories = []
    for sequence, block in enumerate(blocks[1:], start=1):
        block = re.split(r"(?im)^\s*END\s*$", block, maxsplit=1)[0]
        input_id = _field(block, "INPUT")
        item = by_id.get(input_id)
        if not item:
            continue
        headline = _field(block, "HEADLINE")
        summary = _field(block, "SUMMARY")
        evidence = _field(block, "EVIDENCE")
        if not headline or not summary or not evidence:
            continue
        evidence_tokens = _tokens(evidence)
        paragraph_tokens = _tokens(item["paragraph"])
        containment = len(evidence_tokens & paragraph_tokens) / len(evidence_tokens) if evidence_tokens else 0.0
        if containment < 0.75:
            continue
        themes = [x.strip().lower() for x in _field(block, "THEMES").split(",") if x.strip()]
        assets = [x.strip().lower() for x in _field(block, "ASSETS").split(",") if x.strip()]
        entities = [x.strip() for x in _field(block, "ENTITIES").split("|") if x.strip() and x.strip().lower() != "none"]
        catalyst = _field(block, "CATALYST")
        if catalyst.lower() == "none":
            catalyst = ""
        editorial_field = _field(block, "EDITORIAL").lower()
        editorial = editorial_field not in {"no", "false", "0"}
        stories.append(Story(
            f"{input_id}_S{sequence}", headline, summary, evidence, item["source"],
            item["freshness"], themes or [item["theme_hint"].lower()],
            assets or _infer_assets(headline + " " + summary), entities, catalyst,
            bool(re.search(r"\d", evidence)), "ai_labeled_text", editorial,
        ))
    return stories


def extract_stories(newsletters: dict, client=None) -> tuple[list[Story], dict]:
    items = _flatten(newsletters)
    metrics = {"input_count": len(items), "batch_count": 0, "fallback_batches": 0,
               "fallback_inputs": 0, "parsed_inputs": 0, "non_editorial_inputs": 0}
    if not items:
        metrics["quality_pass"] = False
        return [], metrics
    client = client or _client()
    if client is None:
        stories = [_fallback_story(item) for item in items]
        metrics.update(batch_count=1, fallback_batches=1, fallback_inputs=len(items), quality_pass=False)
        return stories, metrics

    system = """Extract distinct market stories. Use only supplied text. Return plain
labeled blocks, never JSON and never Markdown. Each block must be exactly:
STORY
INPUT: N1
HEADLINE: one short factual line
SUMMARY: one factual sentence
EVIDENCE: one exact supporting sentence copied from that input
THEMES: comma-separated themes
ASSETS: comma-separated values from equities, fx, rates, commodities, macro
ENTITIES: names separated by |, or none
CATALYST: supported upcoming event/date/time, or none
EDITORIAL: yes only if this is a real economic, market, company, policy, geopolitical, or investable development; otherwise no
END
Keep every field on one physical line. Do not merge inputs. Mark promotions, cashback/referral offers, broker/service descriptions, unsubscribe/privacy/account-management text, disclaimers, and customer-support copy as EDITORIAL: no.
Return at least one complete STORY ... END block for EVERY supplied INPUT.
The INPUT field must exactly copy the supplied input id. Never omit STORY, INPUT,
HEADLINE, EVIDENCE, or END."""
    all_stories = []
    raw_log_path = os.path.join(getattr(config, "DEBUG_DIR", "debug"), f"extraction_raw_{utils.now_local():%Y%m%d_%H%M%S}.txt")
    raw_log_entries = []
    for start in range(0, len(items), STORY_EXTRACTION_BATCH_SIZE):
        batch = items[start:start + STORY_EXTRACTION_BATCH_SIZE]
        metrics["batch_count"] += 1
        payload = "\n\n".join(
            f"INPUT {x['input_id']}\nSOURCE: {x['source']}\nSUBJECT: {x['subject']}\nTEXT: {x['paragraph']}"
            for x in batch
        )
        try:
            response = _text_call(client, system, payload, max_tokens=max(2200, 550 * len(batch)))
            parsed = _parse_story_blocks(response, batch)
            represented = {story.story_id.split("_S", 1)[0] for story in parsed}
            missing = [item for item in batch if item["input_id"] not in represented]
            recovery_response = ""
            if missing:
                recovery_payload = "\n\n".join(
                    f"INPUT {x['input_id']}\nSOURCE: {x['source']}\nSUBJECT: {x['subject']}\nTEXT: {x['paragraph']}"
                    for x in missing
                )
                recovery_system = system + "\nThis is a repair pass. Return complete blocks only for the supplied missing inputs."
                try:
                    recovery_response = _text_call(
                        client, recovery_system, recovery_payload,
                        max_tokens=max(900, 700 * len(missing)),
                    )
                    recovered = _parse_story_blocks(recovery_response, missing)
                    parsed.extend(recovered)
                    represented = {story.story_id.split("_S", 1)[0] for story in parsed}
                    missing = [item for item in batch if item["input_id"] not in represented]
                except Exception as recovery_exc:
                    utils.log(f"[RANK] Extraction recovery failed ({recovery_exc}); unresolved inputs will use paragraph fallback.")

            represented_ids = {story.story_id.split("_S", 1)[0] for story in parsed}
            editorial_parsed = [story for story in parsed if _is_editorial_story(story)]
            rejected_ids = represented_ids - {story.story_id.split("_S", 1)[0] for story in editorial_parsed}
            fallbacks = [_fallback_story(item) for item in missing]
            editorial_fallbacks = [story for story in fallbacks if _is_editorial_story(story)]
            metrics["non_editorial_inputs"] += len(rejected_ids) + (len(fallbacks) - len(editorial_fallbacks))
            all_stories.extend(editorial_parsed)
            all_stories.extend(editorial_fallbacks)
            metrics["parsed_inputs"] += len(represented_ids)
            metrics["fallback_inputs"] += len(missing)
            if missing:
                utils.log(f"[RANK] Extraction batch {metrics['batch_count']} partially parsed; {len(missing)} input(s) used paragraph fallback.")
                raw_log_entries.append(
                    f"=== batch {metrics['batch_count']} | missing {[m['input_id'] for m in missing]} ===\n"
                    f"--- prompt ---\n{payload}\n--- response ---\n{response}\n"
                    f"--- recovery response ---\n{recovery_response}\n"
                )
        except Exception as exc:
            metrics["fallback_batches"] += 1
            metrics["fallback_inputs"] += len(batch)
            fallbacks = [_fallback_story(item) for item in batch]
            editorial_fallbacks = [story for story in fallbacks if _is_editorial_story(story)]
            metrics["non_editorial_inputs"] += len(fallbacks) - len(editorial_fallbacks)
            all_stories.extend(editorial_fallbacks)
            utils.log(f"[RANK] Extraction batch {metrics['batch_count']} failed ({exc}); paragraph fallback used.")
    if raw_log_entries:
        try:
            with open(raw_log_path, "w", encoding="utf-8") as handle:
                handle.write("\n\n".join(raw_log_entries))
            utils.log(f"[RANK] Raw extraction diagnostics saved: {raw_log_path}")
        except Exception as exc:
            utils.log(f"[RANK] Raw extraction diagnostic save failed: {exc}")
    share = metrics["fallback_inputs"] / max(1, metrics["input_count"])
    metrics["fallback_share"] = round(share, 3)
    metrics["quality_pass"] = share <= MAX_EXTRACTION_FALLBACK_SHARE
    utils.log(f"[RANK] Extracted {len(all_stories)} editorial story candidates; fallback share {share:.0%}; rejected non-editorial inputs {metrics['non_editorial_inputs']}.")
    return all_stories, metrics


def _similarity(left: Story, right: Story) -> float:
    return (
        0.35 * _jaccard(_tokens(left.headline), _tokens(right.headline)) +
        0.25 * _jaccard(_tokens(left.summary), _tokens(right.summary)) +
        0.15 * _jaccard({x.lower() for x in left.entities}, {x.lower() for x in right.entities}) +
        0.10 * _jaccard(set(left.assets), set(right.assets)) +
        0.15 * SequenceMatcher(None, left.headline.lower(), right.headline.lower()).ratio()
    )


def _clearly_same(left: Story, right: Story) -> bool:
    score = _similarity(left, right)
    entities = {x.lower() for x in left.entities} & {x.lower() for x in right.entities}
    assets = set(left.assets) & set(right.assets)
    theme_overlap = _jaccard({x.lower() for x in left.themes}, {x.lower() for x in right.themes})
    headline_overlap = _jaccard(_tokens(left.headline), _tokens(right.headline))
    summary_overlap = _jaccard(_tokens(left.summary), _tokens(right.summary))
    same_source = _clean(left.source).lower() == _clean(right.source).lower()

    same_source_duplicate = same_source and (
        (theme_overlap >= 0.40 and score >= 0.26 and bool(assets))
        or (theme_overlap >= 0.34 and max(headline_overlap, summary_overlap) >= 0.28)
        or (headline_overlap >= 0.42 and bool(assets))
    )
    return (
        score >= 0.58
        or (score >= 0.36 and bool(entities))
        or (score >= 0.22 and bool(entities) and bool(assets))
        or same_source_duplicate
    )


def _borderline(stories: list[Story]) -> list[tuple[int, int, float]]:
    output = []
    for i in range(len(stories)):
        for j in range(i + 1, len(stories)):
            score = _similarity(stories[i], stories[j])
            if 0.25 <= score < 0.58:
                output.append((i, j, score))
    return sorted(output, key=lambda x: x[2], reverse=True)[:12]


def _adjudicate(stories, pairs, client) -> tuple[set[tuple[int, int]], bool]:
    """Parse lines like 1=SAME. Failure is non-blocking; Python clustering remains."""
    if not pairs or client is None:
        return set(), True
    prompt = []
    for n, (i, j, _) in enumerate(pairs, 1):
        prompt.append(f"PAIR {n}\nA: {stories[i].headline} | {stories[i].summary}\nB: {stories[j].headline} | {stories[j].summary}")
    system = """Decide whether each pair is the same underlying market development.
Different central banks, companies, events, or competing causes are DIFFERENT.
Return one line per pair only, for example 1=SAME or 2=DIFFERENT. No JSON."""
    try:
        text = _text_call(client, system, "\n\n".join(prompt), max_tokens=300)
        decisions = {int(n): value.upper() for n, value in re.findall(r"(?im)^\s*(\d+)\s*=\s*(SAME|DIFFERENT)\s*$", text)}
        approved = set()
        for n, (i, j, _) in enumerate(pairs, 1):
            if decisions.get(n) == "SAME":
                approved.add((i, j))
        return approved, len(decisions) == len(pairs)
    except Exception as exc:
        utils.log(f"[RANK] Borderline review failed ({exc}); deterministic clustering retained.")
        return set(), False


def cluster_stories(stories: list[Story], client=None) -> tuple[list[Cluster], dict]:
    if not stories:
        return [], {"borderline_complete": False}
    client = client or _client()
    parent = list(range(len(stories)))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def union(a, b):
        a, b = find(a), find(b)
        if a != b: parent[b] = a
    for i in range(len(stories)):
        for j in range(i + 1, len(stories)):
            if _clearly_same(stories[i], stories[j]): union(i, j)
    adjudication_client = client if ENABLE_AI_BORDERLINE_ADJUDICATION else None
    approved, complete = _adjudicate(stories, _borderline(stories), adjudication_client)
    for i, j in approved: union(i, j)
    groups = defaultdict(list)
    for i, story in enumerate(stories): groups[find(i)].append(story)
    clusters = []
    for number, members in enumerate(groups.values(), 1):
        canonical = max(members, key=lambda s: (s.has_supported_number, len(s.entities), len(s.summary)))
        clusters.append(Cluster(
            f"C{number}", canonical.headline, canonical.summary,
            list(dict.fromkeys(x.evidence for x in members if x.evidence)),
            list(dict.fromkeys(x.source for x in members if x.source)),
            list(dict.fromkeys(t for x in members for t in x.themes)),
            list(dict.fromkeys(a for x in members for a in x.assets)),
            list(dict.fromkeys(e for x in members for e in x.entities)),
            list(dict.fromkeys(x.catalyst for x in members if x.catalyst)),
            list(dict.fromkeys(x.freshness for x in members if x.freshness)),
            [x.story_id for x in members], list(dict.fromkeys(x.extraction_method for x in members)),
        ))
    utils.log(f"[RANK] Grouped candidates into {len(clusters)} story clusters.")
    return clusters, {"borderline_complete": complete}


def _market_scores(market):
    equity = max([abs(x.get("ret_1d") or 0) for x in market.get("equities", {}).values()] or [0])
    fx = max([abs(x.get("ret_1d") or 0) for x in market.get("fx", {}).values()] or [0])
    rates = max([abs(x["latest"] - x["prev"]) * 100 for x in market.get("rates", {}).values() if x.get("latest") is not None and x.get("prev") is not None] or [0])
    return {"equities": min(20, equity / 0.01 * 10), "fx": min(20, fx / 0.005 * 10), "rates": min(20, rates / 5 * 10), "commodities": 0, "macro": 0}


def score_clusters(clusters, market, recent_titles=None):
    recent_titles = recent_titles or []
    moves = _market_scores(market)
    for c in clusters:
        coverage = {1: 5, 2: 12, 3: 18}.get(len(c.sources), 25 if len(c.sources) >= 4 else 0)
        market_move = max([moves.get(a, 0) for a in c.assets] or [0])
        cross_asset = min(15, max(5, len(set(c.assets)) * 5))
        recent_similarity = max([_jaccard(_tokens(c.canonical_story), _tokens(x)) for x in recent_titles] or [0])
        freshness = 15 if "today" in " ".join(c.freshness_labels).lower() else 10
        if recent_similarity >= 0.45: freshness = min(freshness, 6)
        forward = 10 if c.catalysts else 0
        usefulness = min(10, 4 + 2 * len(set(c.assets)) + (2 if any(re.search(r"\d", e) for e in c.evidence) else 0))
        types = set()
        for source in c.sources:
            lower = source.lower()
            types.add("specialist" if any(x in lower for x in SPECIALIST_MARKERS) else "general")
        diversity = 3 if len(types) >= 2 else 1
        specialist = ALLOW_SPECIALIST_EXCEPTION and len(c.sources) == 1 and "specialist" in types and market_move >= 5 and usefulness >= 6
        c.specialist_exception = specialist
        c.score_breakdown = {
            "cross_publication_coverage": coverage, "market_move": round(market_move, 1),
            "cross_asset": cross_asset, "freshness": freshness, "forward_relevance": forward,
            "reader_usefulness": usefulness, "source_diversity": diversity,
            "specialist_bonus": 8 if specialist else 0,
        }
        c.score = round(sum(c.score_breakdown.values()), 1)
    return sorted(clusters, key=lambda c: c.score, reverse=True)


def _cluster_distinctiveness(left, right):
    title_overlap = _jaccard(_tokens(left.canonical_story), _tokens(right.canonical_story))
    theme_overlap = _jaccard({x.lower() for x in left.themes}, {x.lower() for x in right.themes})
    entity_overlap = _jaccard({x.lower() for x in left.entities}, {x.lower() for x in right.entities})
    return 1.0 - (0.50 * title_overlap + 0.35 * theme_overlap + 0.15 * entity_overlap)


def select_editorial_package(clusters):
    if not clusters:
        return {"lead_story": None, "parallax_inputs": [], "headline_clusters": [],
                "watch_items": [], "open_question_inputs": [], "ranked_clusters": []}

    lead = next((c for c in clusters if c.score_breakdown.get("market_move", 0) > 0), clusters[0])
    selected = [lead]

    for c in clusters:
        if c.cluster_id == lead.cluster_id:
            continue
        distinct = min(_cluster_distinctiveness(c, existing) for existing in selected)
        if distinct < 0.58 and not c.specialist_exception:
            continue
        selected.append(c)
        if len(selected) >= TARGET_SELECTED_STORIES:
            break

    if len(selected) < MIN_SELECTED_STORIES:
        for c in clusters:
            if c not in selected:
                selected.append(c)
            if len(selected) >= MIN_SELECTED_STORIES:
                break

    selected = selected[:min(MAX_SELECTED_STORIES, TARGET_SELECTED_STORIES)]

    partner = next((c for c in selected if c != lead and _cluster_distinctiveness(c, lead) >= 0.45), None)
    parallax = [lead] + ([partner] if partner else [])
    watches = list(dict.fromkeys(x for c in selected for x in c.catalysts))[:4]
    open_inputs = selected[:2]
    return {
        "lead_story": asdict(lead),
        "parallax_inputs": [asdict(c) for c in parallax],
        "headline_clusters": [asdict(c) for c in selected],
        "watch_items": watches,
        "open_question_inputs": [asdict(c) for c in open_inputs],
        "ranked_clusters": [asdict(c) for c in clusters],
    }


def build_ranked_package(newsletters, market, recent_titles=None):
    client = _client()
    stories, extraction = extract_stories(newsletters, client)
    clusters, clustering = cluster_stories(stories, client)
    ranked = score_clusters(clusters, market, recent_titles)
    package = select_editorial_package(ranked)
    package["quality"] = {
        "extraction": extraction, "clustering": clustering,
        "ranking_pass": bool(package.get("lead_story")) and len(package.get("headline_clusters", [])) >= MIN_SELECTED_STORIES,
    }
    package["quality"]["pass"] = bool(extraction.get("quality_pass") and package["quality"]["ranking_pass"])
    utils.log(f"[RANK] Ranked {len(ranked)} clusters; selected {len(package['headline_clusters'])}.")
    return package