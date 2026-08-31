"""Cohesive full-edition synthesis without JSON.

One model call writes the whole newsletter in one voice. A second call edits
that edition for coherence, grounding, and repetition. Python owns the labeled
plain-text contract and all publication gating.
"""
from __future__ import annotations

import os
import re
import time

import config
import utils

try:
    from openai import OpenAI
    OPENAI_SDK_AVAILABLE = True
except Exception:
    OPENAI_SDK_AVAILABLE = False

BEGIN = "BEGIN BRIEF"
END = "END BRIEF"
CORE_LABELS = [
    "TITLE", "RISK MOOD", "OPENING", "KEY LINE", "MARKET READ",
    "PARALLAX TITLE", "PARALLAX", "WHAT'S MOVING", "OPEN QUESTION",
    "OPEN ANSWER",
]


def _daily_quota_exhausted(message):
    text = str(message or "")
    lower = text.lower()
    return (
        "GenerateRequestsPerDayPerProjectPerModel-FreeTier" in text
        or "requests_per_day" in lower
        or "requests per day" in lower
        or "perdayperprojectpermodel" in lower
    )


def _wait_for_shared_ai_slot():
    """Share one process-wide Gemini pacing clock with story_ranker."""
    min_interval = getattr(config, "AI_MIN_CALL_INTERVAL_SECONDS", 13.0)
    last_call = getattr(config, "_AI_LAST_CALL_TIME", 0.0)

    if last_call:
        elapsed = time.monotonic() - last_call
        if elapsed < min_interval:
            wait = min_interval - elapsed
            utils.log(f"[AI] Rate-limit pacing: waiting {wait:.1f}s.")
            time.sleep(wait)

    config._AI_LAST_CALL_TIME = time.monotonic()


def _clean(value):
    return re.sub(r"\s+", " ", str(value or "").replace("—", ", ").replace("–", ", ")).strip()


def _client():
    if not OPENAI_SDK_AVAILABLE:
        return None
    key = os.environ.get(config.AI_API_KEY_ENV, "").strip()
    return None if not key else OpenAI(api_key=key, base_url=config.AI_BASE_URL)


def _call(client, system, user, max_tokens=None):
    kwargs = {
        "model": config.AI_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": getattr(config, "AI_TEMPERATURE", 0.1),
        "max_tokens": max_tokens or getattr(config, "AI_MAX_TOKENS", 6500),
    }

    reasoning_effort = getattr(config, "AI_REASONING_EFFORT", "low")
    if reasoning_effort:
        kwargs["reasoning_effort"] = reasoning_effort

    if getattr(config, "_AI_DAILY_QUOTA_EXHAUSTED", False):
        raise RuntimeError("Gemini daily free-tier request quota exhausted.")

    _wait_for_shared_ai_slot()

    try:
        response = client.chat.completions.create(**kwargs)

    except Exception as exc:
        message = str(exc)

        if _daily_quota_exhausted(message):
            config._AI_DAILY_QUOTA_EXHAUSTED = True
            raise RuntimeError(
                "Gemini daily free-tier request quota exhausted."
            ) from exc

        is_rpm_limit = (
            "GenerateRequestsPerMinute" in message
            or "requests_per_minute" in message.lower()
            or "requests per minute" in message.lower()
        )
        if not is_rpm_limit:
            raise

        match = re.search(
            r"retry(?:Delay| in)?[^0-9]*(\d+(?:\.\d+)?)s",
            message,
            re.I,
        )
        wait_seconds = min(
            65.0,
            max(
                getattr(config, "AI_MIN_CALL_INTERVAL_SECONDS", 13.0),
                float(match.group(1)) + 1.0 if match else 20.0,
            ),
        )

        utils.log(
            "[AI] Per-minute quota reached; "
            f"retrying once after {wait_seconds:.0f}s."
        )
        time.sleep(wait_seconds)

        if getattr(config, "_AI_DAILY_QUOTA_EXHAUSTED", False):
            raise RuntimeError("Gemini daily free-tier request quota exhausted.")

        config._AI_LAST_CALL_TIME = time.monotonic()
        response = client.chat.completions.create(**kwargs)

    choice = response.choices[0]
    content = (choice.message.content or "").strip()
    usage = getattr(response, "usage", None)
    finish_reason = getattr(choice, "finish_reason", None)

    utils.log(
        "[AI] "
        f"finish_reason={finish_reason} "
        f"prompt_tokens={getattr(usage, 'prompt_tokens', None)} "
        f"completion_tokens={getattr(usage, 'completion_tokens', None)} "
        f"chars={len(content)}"
    )

    if not content:
        raise RuntimeError("AI returned empty content")
    if str(finish_reason).lower() == "length":
        raise RuntimeError(
            "AI response truncated because output token limit was reached"
        )
    return content


def _market_text(market):
    lines = []
    for name, item in market.get("equities", {}).items():
        lines.append(f"EQUITY | {name} | last {item.get('latest')} | chg {utils.format_pct(item.get('ret_1d'))}")
    for name, item in market.get("fx", {}).items():
        lines.append(f"FX | {name} | spot {item.get('latest')} | chg {utils.format_pct(item.get('ret_1d'), 2)}")
    for name, item in market.get("rates", {}).items():
        latest, previous = item.get("latest"), item.get("prev")
        move = "n/a" if latest is None or previous is None else f"{(latest - previous) * 100:+.0f} bp"
        lines.append(f"UST | {name} | yield {latest}% | chg {move}")
    return "\n".join(lines)


def _evidence_lines(cluster, limit=3, max_chars=420):
    evidence = []
    for item in cluster.get("evidence", []) if cluster else []:
        cleaned = _clean(item)
        if not cleaned or cleaned in evidence:
            continue
        evidence.append(cleaned[:max_chars])
        if len(evidence) >= limit:
            break
    return evidence


def _cluster_text(cluster):
    if not cluster:
        return "None"
    evidence = _evidence_lines(cluster)
    lines = [
        f"CLUSTER ID: {cluster.get('cluster_id', '')}",
        f"STORY: {cluster.get('canonical_story', '')}",
        f"SUMMARY: {cluster.get('summary', '')}",
    ]
    if evidence:
        lines.extend(f"EVIDENCE {number}: {text}" for number, text in enumerate(evidence, 1))
    else:
        lines.append("EVIDENCE: none")
    lines.extend([
        f"SOURCES: {' | '.join(cluster.get('sources', []))}",
        f"ASSETS: {', '.join(cluster.get('assets', []))}",
        f"CATALYSTS: {' | '.join(cluster.get('catalysts', [])) or 'none'}",
    ])
    return "\n".join(lines)


def _selected_context(package):
    selected = package.get("headline_clusters", [])
    parts = ["LEAD STORY\n" + _cluster_text(package.get("lead_story"))]
    parts.append("PARALLAX INPUTS\n" + "\n\n".join(_cluster_text(x) for x in package.get("parallax_inputs", [])))
    parts.append("SELECTED HEADLINE CLUSTERS\n" + "\n\n".join(_cluster_text(x) for x in selected))
    parts.append("APPROVED WATCH ITEMS\n" + (" | ".join(package.get("watch_items", [])) or "none"))
    parts.append("OPEN QUESTION INPUTS\n" + "\n\n".join(_cluster_text(x) for x in package.get("open_question_inputs", [])))
    return "\n\n".join(parts)


def _ordered_labels(headline_count):
    labels = CORE_LABELS[:7]
    for number in range(1, headline_count + 1):
        labels.extend([
            f"HEADLINE {number} CLUSTER",
            f"HEADLINE {number}",
            f"HEADLINE {number} SUMMARY",
            f"HEADLINE {number} SOURCES",
        ])
    labels.extend(CORE_LABELS[7:])
    for number in range(1, 5):
        labels.append(f"WATCH {number}")
    return labels


def _normalize_punctuation(raw):
    replacements = {
        "\u2019": "'", "\u2018": "'",
        "\u201c": '"', "\u201d": '"',
        "\u2014": ", ", "\u2013": ", ",
    }
    for original, replacement in replacements.items():
        raw = raw.replace(original, replacement)
    return raw


def _extract_document(raw):
    start = raw.find(BEGIN)
    finish = raw.rfind(END)
    if start < 0 or finish < 0 or finish <= start:
        raise ValueError("missing BEGIN BRIEF or END BRIEF marker")
    return raw[start + len(BEGIN):finish].strip()


def _extract_sections(raw, labels):
    body = _extract_document(raw)
    matches = []
    for label in labels:
        match = re.search(rf"(?im)^\s*{re.escape(label)}\s*:\s*", body)
        if match:
            matches.append((match.start(), match.end(), label))
    matches.sort()
    sections = {}
    for index, (_, content_start, label) in enumerate(matches):
        content_end = matches[index + 1][0] if index + 1 < len(matches) else len(body)
        sections[label] = body[content_start:content_end].strip()
    return sections


_ABBREVIATIONS = (
    "U.S.", "U.K.", "U.N.", "E.U.", "vs.", "etc.", "approx.", "Inc.", "Corp.",
    "Ltd.", "Co.", "St.", "Jr.", "Sr.", "Mr.", "Mrs.", "Dr.", "e.g.", "i.e.",
    "Fed.", "No.", "Jan.", "Feb.", "Mar.", "Apr.", "Jun.", "Jul.", "Aug.",
    "Sep.", "Sept.", "Oct.", "Nov.", "Dec.",
)


def _sentence_count(text):
    masked = text
    for abbr in _ABBREVIATIONS:
        masked = masked.replace(abbr, abbr.replace(".", "\u2024"))
    return len(re.findall(r"[.!?](?:\s|$)", masked.strip()))


def _content_tokens(text):
    stop = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "is", "it", "of", "on", "or", "the", "to", "was", "were", "while", "with"}
    return {w for w in re.findall(r"[a-z0-9]+", _clean(text).lower()) if len(w) > 2 and w not in stop}


def _token_overlap(left, right):
    a, b = _content_tokens(left), _content_tokens(right)
    return len(a & b) / len(a | b) if a and b else 0.0


def _cluster_lookup(package):
    return {
        _clean(c.get("cluster_id")): c
        for c in package.get("headline_clusters", [])
        if _clean(c.get("cluster_id"))
    }


def _validate_title(title, package):
    errors = []
    cleaned = _clean(title)
    words = re.findall(r"[A-Za-z0-9']+", cleaned)
    if not 2 <= len(words) <= 9:
        errors.append("TITLE must contain between 2 and 9 words")
    lead = package.get("lead_story") or {}
    if lead and _token_overlap(cleaned, lead.get("canonical_story", "")) >= 0.72:
        errors.append("TITLE is too close to the lead-story headline; use a distinctive editorial title")
    summary_pattern = re.compile(r"(?i)^(stocks?|equities|bonds?|yields?|dollar|markets?)\b.*\b(as|while|after|on)\b")
    if summary_pattern.search(cleaned):
        errors.append("TITLE reads like a market recap; use a distinctive editorial idea")
    return errors


def _validate_open_question(question):
    errors = []
    cleaned = _clean(question)
    words = re.findall(r"[A-Za-z0-9']+", cleaned)
    if _sentence_count(cleaned) != 1 or not cleaned.endswith("?"):
        errors.append("OPEN QUESTION must be exactly one question")
    if not 5 <= len(words) <= 18:
        errors.append("OPEN QUESTION must contain between 5 and 18 words")
    if words and words[0].lower() not in {"why", "how", "what", "when", "can", "does", "do", "could"}:
        errors.append("OPEN QUESTION should begin with a simple interview-style question word")
    jargon = (
        "term premium", "duration-sensitive", "duration sensitive", "convexity",
        "basis trade", "cross gamma", "realized volatility", "implied volatility",
        "discounted cash flow", "multiple compression", "yield-curve inversion",
    )
    lower = cleaned.lower()
    if any(term in lower for term in jargon):
        errors.append("OPEN QUESTION contains avoidable market jargon")
    return errors


def _validate(sections, package):
    errors = []
    expected_headlines = len(package.get("headline_clusters", []))
    lookup = _cluster_lookup(package)

    for label in CORE_LABELS:
        if not _clean(sections.get(label)):
            errors.append(f"missing {label}")
    for number in range(1, expected_headlines + 1):
        for suffix in (" CLUSTER", "", " SUMMARY", " SOURCES"):
            label = f"HEADLINE {number}{suffix}"
            if not _clean(sections.get(label)):
                errors.append(f"missing {label}")

    errors.extend(_validate_title(sections.get("TITLE", ""), package))

    if sections.get("OPENING") and _sentence_count(sections["OPENING"]) != 1:
        errors.append("OPENING must contain exactly one sentence")
    if sections.get("KEY LINE") and _sentence_count(sections["KEY LINE"]) != 1:
        errors.append("KEY LINE must contain exactly one sentence")
    if sections.get("MARKET READ"):
        market_read_sentences = _sentence_count(sections["MARKET READ"])
        if not 1 <= market_read_sentences <= 3:
            errors.append("MARKET READ must contain between one and three sentences")
    if sections.get("PARALLAX") and _sentence_count(sections["PARALLAX"]) != 3:
        errors.append("PARALLAX must contain exactly three sentences")
    if sections.get("OPEN ANSWER") and _sentence_count(sections["OPEN ANSWER"]) != 3:
        errors.append("OPEN ANSWER must contain exactly three sentences")
    if sections.get("OPEN QUESTION"):
        errors.extend(_validate_open_question(sections["OPEN QUESTION"]))

    # Cluster IDs make story/source validation independent of model ordering.
    shown_cluster_ids = []
    for number in range(1, expected_headlines + 1):
        cluster_id = _clean(sections.get(f"HEADLINE {number} CLUSTER"))
        shown_cluster_ids.append(cluster_id)
        cluster = lookup.get(cluster_id)
        if cluster is None:
            errors.append(f"HEADLINE {number} CLUSTER is not an approved selected cluster")
            continue
        line = sections.get(f"HEADLINE {number} SOURCES", "")
        shown = {_clean(x) for x in line.split("|") if _clean(x)}
        allowed = {_clean(x) for x in cluster.get("sources", []) if _clean(x)}
        if not shown or not shown.issubset(allowed):
            errors.append(f"HEADLINE {number} SOURCES contains an unapproved source")

        headline = _clean(sections.get(f"HEADLINE {number}"))
        summary = _clean(sections.get(f"HEADLINE {number} SUMMARY"))
        if headline and summary and _token_overlap(headline, summary) >= 0.78:
            errors.append(f"HEADLINE {number} SUMMARY mostly restates its headline")

    approved_ids = set(lookup)
    if set(shown_cluster_ids) != approved_ids or len(shown_cluster_ids) != len(set(shown_cluster_ids)):
        errors.append("headline cluster IDs must use every selected cluster exactly once")

    # WATCH catalyst text is owned by Python, not the model.
    # Model WATCH fields are ignored when building the final result.

    # Guard the most common repetitive failure modes without trying to score prose aesthetics.
    if sections.get("OPENING") and sections.get("KEY LINE") and _token_overlap(sections["OPENING"], sections["KEY LINE"]) >= 0.78:
        errors.append("KEY LINE is too repetitive with OPENING")
    if sections.get("MARKET READ") and sections.get("PARALLAX") and _token_overlap(sections["MARKET READ"], sections["PARALLAX"]) >= 0.72:
        errors.append("PARALLAX is too repetitive with MARKET READ")
    if sections.get("OPEN QUESTION") and sections.get("KEY LINE") and _token_overlap(sections["OPEN QUESTION"], sections["KEY LINE"]) >= 0.72:
        errors.append("OPEN QUESTION is too repetitive with KEY LINE")
    return errors


def _approved_watch_items(package, limit=4):
    """Return exact Python-approved watch items, deduplicated in order."""
    output = []
    seen = set()

    for item in package.get("watch_items", []):
        cleaned = _clean(item)
        key = cleaned.lower()

        if not cleaned or key in seen:
            continue

        seen.add(key)
        output.append(cleaned)

        if len(output) >= limit:
            break

    return output


def _template(headline_count):
    lines = [
        BEGIN, "TITLE:", "RISK MOOD:", "OPENING:", "KEY LINE:",
        "MARKET READ:", "PARALLAX TITLE:", "PARALLAX:",
    ]
    for number in range(1, headline_count + 1):
        lines.extend([
            f"HEADLINE {number} CLUSTER:",
            f"HEADLINE {number}:",
            f"HEADLINE {number} SUMMARY:",
            f"HEADLINE {number} SOURCES:",
        ])
    lines.extend(["WHAT'S MOVING:"])
    for number in range(1, 5):
        lines.append(f"WATCH {number}:")
    lines.extend(["OPEN QUESTION:", "OPEN ANSWER:", END])
    return "\n".join(lines)


def _writing_system():
    return """You are the sole editor of Parallax, a concise markets publication for intelligent non-specialists and students preparing for markets interviews. Write the complete edition as one coherent morning read. Every section has a different job; repetition is a quality failure.

GROUNDING
Use only supplied market data, selected clusters, evidence, approved source names, and approved watch items. Never invent a number, date, time, quotation, event, cause, implication, source, or catalyst. Treat causality as interpretation unless directly supported. Do not give investment advice, price targets, or buy/sell language.

TITLE
Create a short, distinctive editorial title built around the edition's central tension, contrast, or idea. It should spark curiosity and still make sense after markets close. Do NOT simply summarize market direction, reuse the lead-story headline, list assets, or use formulas such as 'Stocks rise as yields fall', 'X while Y', or 'X amid Y'. Prefer memorable conceptual titles like 'Two Economies, One Market' rather than wire-service recap headlines.

SECTION JOBS
OPENING: exactly one sentence. Orient the reader to what matters today without repeating the title or listing table values.
KEY LINE: exactly one sentence. State the one implication worth remembering. It must add something beyond OPENING.
MARKET READ: one to three concise sentences. Interpret the cross-asset pattern. The snapshot below will show exact levels, so do not recap every index, FX pair, or Treasury maturity.
PARALLAX: exactly three sentences. Connect at least two DIFFERENT selected developments, assets, or perspectives. Sentence 1 establishes the relationship, sentence 2 explains why it matters, sentence 3 states the tension or implication. Do not simply restate the lead story or MARKET READ.
WORTH KNOWING: use every selected cluster exactly once, but you may reorder non-lead stories editorially. Copy its CLUSTER ID exactly into the matching HEADLINE N CLUSTER field. Each headline should be concise. Each summary should explain rather than echo the headline. Usually use two sentences when evidence supports it: what happened, then why it matters or what context makes it useful. If evidence is thin, use one strong factual sentence instead of padding.
WHAT'S MOVING: one concise sentence only when an immediate driver/catalyst adds genuinely new information. Otherwise write exactly: none
OPEN QUESTION: one short, plain-English interview-prep question inspired by today's edition. It should teach a reusable market concept, not test trivia about today's source. It must be answerable without calculations or specialist jargon. Prefer simple questions such as 'Why can higher bond yields hurt stocks?' or 'Why does a stronger dollar matter for companies?' Do not ask a vague question such as 'What would change the market narrative?'
OPEN ANSWER: exactly three teaching sentences. Sentence 1 gives the direct answer in plain English. Sentence 2 explains the mechanism. Sentence 3 explains what a markets interviewer/investor would therefore watch. Stay grounded in supplied facts and general relationships already implicit in the question; do not invent a future event.

STYLE
Write for a smart university student who wants to understand markets, not for a terminal screen. Prefer concrete nouns and verbs. No emojis, em dashes, en dashes, first person, forced three-part rhetorical lists, or stock AI phrases such as amid, underscores, notably, robust, the takeaway, it is worth noting, let us dive in, when it comes to, or a testament to.

OUTPUT CONTRACT
Return only the provided plain-text template. Keep every label exactly unchanged. Include BEGIN BRIEF and END BRIEF. Use only approved source names. Python owns the final watch list, so write exactly 'none' in WATCH 1 through WATCH 4. Do not add or remove headline slots."""


def _editor_system():
    return """You are the final senior editor of Parallax. Edit the complete draft as one document for grounding, clarity, interview usefulness, and economy.

REPETITION TEST
The title, Opening, Key Line, Market Read, Parallax, Worth Knowing summaries, and Open Question must each contribute a different idea. A named company or lead story should not dominate every major section. Rewrite sentences that merely paraphrase something already stated. Market Read interprets the tables; it does not narrate them.

TITLE TEST
The title must be a distinctive editorial idea, not a market recap or a rewritten lead headline. Favor curiosity, tension, or contrast.

PARALLAX TEST
The Parallax must connect at least two genuinely different inputs and explain why the relationship matters. Reject generic filler about 'multiple angles', 'prices show what moved', or comparing publications.

WORTH KNOWING TEST
Every selected CLUSTER ID must appear exactly once. Preserve the CLUSTER field when reordering stories. Summaries should provide useful explanation and should not simply restate their headline. Never pad weak evidence.

OPEN QUESTION TEST
Treat this as a daily markets-interview learning prompt. It must be short, plain English, reusable beyond today's story, and answerable by reasoning. The three-sentence answer should directly answer, explain the mechanism, then say what one would watch. Avoid trivia, vague narrative questions, and unexplained jargon.

GROUNDING
Use only supplied market data, selected clusters, evidence, approved sources, and approved watch items. Do not add unsupported facts, numbers, dates, causes, implications, catalysts, or sources. Python owns the final watch list, so keep WATCH 1 through WATCH 4 as exactly 'none'.

Return the full plain-text template only. Keep every label, cluster ID field, BEGIN BRIEF, and END BRIEF. Do not add or remove headline slots. PARALLAX and OPEN ANSWER must each contain exactly three sentences. OPENING and KEY LINE must each contain one sentence. WHAT'S MOVING may be exactly 'none'. No JSON, Markdown, emojis, em dashes, en dashes, or commentary outside the template."""


def _repair_system():
    return """You are repairing a Parallax draft that failed deterministic validation. Return the complete corrected plain-text template only. Preserve every supported claim that is already valid. Fix only the supplied validation errors plus obvious template breakage. Do not add facts, sources, dates, numbers, events, causes, implications, or watch items. Python owns the final watch list, so keep WATCH 1 through WATCH 4 as exactly 'none'. Keep every label exactly unchanged, preserve every approved HEADLINE N CLUSTER value exactly once, and include BEGIN BRIEF and END BRIEF. PARALLAX and OPEN ANSWER must each contain exactly three sentences. No JSON, Markdown, emojis, em dashes, en dashes, or commentary."""


def _build_user(reference_dt, market, package, draft=None, repair_errors=None):
    parts = [
        f"DATE\n{reference_dt:%A, %B %d, %Y}",
        "MARKET DATA\n" + _market_text(market),
        "RANKED EDITORIAL PACKAGE\n" + _selected_context(package),
    ]
    if draft is not None:
        parts.append("DRAFT TO EDIT\n" + draft)
    if repair_errors:
        parts.append("VALIDATION ERRORS TO FIX\n- " + "\n- ".join(repair_errors))
    parts.append("REQUIRED TEMPLATE\n" + _template(len(package.get("headline_clusters", []))))
    return "\n\n".join(parts)


def _parse_to_result(raw, package):
    labels = _ordered_labels(len(package.get("headline_clusters", [])))
    sections = _extract_sections(raw, labels)
    errors = _validate(sections, package)
    if errors:
        raise ValueError("; ".join(errors))

    headlines = []
    lookup = _cluster_lookup(package)
    for number in range(1, len(package.get("headline_clusters", [])) + 1):
        cluster_id = _clean(sections[f"HEADLINE {number} CLUSTER"])
        cluster = lookup[cluster_id]
        sources = [
            _clean(x)
            for x in sections[f"HEADLINE {number} SOURCES"].split("|")
            if _clean(x)
        ]
        headlines.append({
            "headline": _clean(sections[f"HEADLINE {number}"]),
            "summary": _clean(sections[f"HEADLINE {number} SUMMARY"]),
            "source": ", ".join(sources),
            "cluster_id": cluster_id,
        })

    # Exact catalyst strings come directly from the deterministic ranked package.
    watch = _approved_watch_items(package)

    moving = _clean(sections["WHAT'S MOVING"])
    if moving.lower() == "none":
        moving = ""

    return {
        "daily_title": _clean(sections["TITLE"]),
        "sentiment": _clean(sections["RISK MOOD"]),
        "mood": _clean(sections["OPENING"]),
        "key_line": _clean(sections["KEY LINE"]),
        # Keep the existing dictionary key for compatibility with brief_builder;
        # it now contains one interpretive Market Read and no per-asset prose.
        "market_summary": {"overview": _clean(sections["MARKET READ"]), "movements": []},
        "parallax": {
            "title": _clean(sections["PARALLAX TITLE"]),
            "text": _clean(sections["PARALLAX"]),
        },
        "top_headlines": headlines,
        "whats_moving": {"story": moving, "watch": watch},
        "open_question": {
            "question": _clean(sections["OPEN QUESTION"]),
            "answer": _clean(sections["OPEN ANSWER"]),
        },
        "engine": "cohesive_plain_text",
        "quality": {"pass": True, "failed_sections": []},
    }


def _fallback(market, package):
    # Fallback is an internal diagnostic artifact, not substitute journalism.
    selected = package.get("headline_clusters", [])
    return {
        "daily_title": "INTERNAL REVIEW ONLY: synthesis failed",
        "sentiment": "Unavailable",
        "mood": "",
        "key_line": "",
        "market_summary": {"overview": "", "movements": []},
        "parallax": {"title": "", "text": ""},
        "top_headlines": [
            {
                "headline": c.get("canonical_story", ""),
                "summary": c.get("summary", ""),
                "source": ", ".join(c.get("sources", [])),
                "cluster_id": c.get("cluster_id", ""),
            }
            for c in selected
        ],
        "whats_moving": {"story": "", "watch": []},
        "open_question": {"question": "", "answer": ""},
        "engine": "diagnostic_fallback",
        "quality": {"pass": False, "failed_sections": ["full_edition"]},
    }


def synthesize(market, ranked_package, reference_dt):
    client = _client()
    if client is None:
        utils.log("[SYNTH] Gemini unavailable; deterministic fallback used.")
        return _fallback(market, ranked_package)

    raw = ""
    result = None
    validation_errors = []

    for attempt in range(2):
        request_succeeded = False
        try:
            system = _writing_system() if attempt == 0 else _repair_system()
            raw = _call(
                client,
                system,
                _build_user(
                    reference_dt,
                    market,
                    ranked_package,
                    draft=raw if attempt else None,
                    repair_errors=validation_errors if attempt else None,
                ),
                max_tokens=getattr(config, "AI_MAX_TOKENS", 6500),
            )
            request_succeeded = True
            raw = _normalize_punctuation(raw)
            result = _parse_to_result(raw, ranked_package)
            break
        except Exception as exc:
            validation_errors = [str(exc)]
            utils.log(f"[SYNTH] Full draft validation failed on attempt {attempt + 1}: {exc}")

            if request_succeeded:
                try:
                    path = os.path.join(
                        getattr(config, "DEBUG_DIR", "debug"),
                        f"synth_raw_{reference_dt:%Y%m%d_%H%M%S}_attempt{attempt + 1}.txt",
                    )
                    with open(path, "w", encoding="utf-8") as handle:
                        handle.write(raw)
                    utils.log(f"[SYNTH] Raw draft diagnostics saved: {path}")
                except Exception:
                    pass

            message = str(exc)
            if "RESOURCE_EXHAUSTED" in message or "429" in message:
                utils.log("[SYNTH] Quota exhausted; skipping retry.")
                break
            if "truncated because output token limit" in message:
                raw = ""

    if result is None:
        utils.log("[SYNTH] Full draft failed after retry; deterministic fallback used.")
        return _fallback(market, ranked_package)

    try:
        edited_raw = _call(
            client,
            _editor_system(),
            _build_user(reference_dt, market, ranked_package, draft=raw),
            max_tokens=getattr(config, "AI_MAX_TOKENS", 6500),
        )
        edited_raw = _normalize_punctuation(edited_raw)
        edited = _parse_to_result(edited_raw, ranked_package)
        edited["quality"] = {"pass": True, "failed_sections": [], "editor_pass": True}
        utils.log("[SYNTH] Cohesive full draft and holistic editor pass completed.")
        return edited
    except Exception as exc:
        allow = getattr(config, "ALLOW_VALID_UNEDITED_DRAFT", False)
        result["quality"] = {
            "pass": bool(allow),
            "failed_sections": ["holistic_editor"],
            "editor_pass": False,
        }
        utils.log(
            f"[SYNTH] Holistic editor failed ({exc}); valid writer draft retained. "
            f"Quality pass: {bool(allow)}."
        )
        return result
