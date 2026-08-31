"""Parallax orchestration with cohesive-synthesis publication gate."""
import json
import os
import sys
from datetime import datetime

import config
import utils
import market_data
import gmail_client
import email_parser
import newsletter_filter
import story_memory
import story_ranker
import synthesis
import brief_builder
import email_sender
import subscriber_store
import broadcast_sender


CANDIDATE_FILENAME = "dry_run_candidate.json"


def _recent_titles(reference_dt):
    try:
        block, _ = story_memory.load_recent(reference_dt)
        return [
            line.strip().lstrip("- ").split(" (covered", 1)[0]
            for line in str(block).splitlines()
            if line.strip() and line.strip().lower() != "none."
        ]
    except Exception:
        return []


def _redact(value):
    if isinstance(value, dict):
        return {
            key: _redact(item)
            for key, item in value.items()
            if key != "evidence"
        }

    if isinstance(value, list):
        return [_redact(item) for item in value]

    return value


def _candidate_path():
    return os.path.join(config.DEBUG_DIR, CANDIDATE_FILENAME)


def _invalidate_candidate():
    """Remove any prior sendable candidate before generating a new dry run."""
    path = _candidate_path()

    if not os.path.exists(path):
        return

    try:
        os.remove(path)
        utils.log("[PIPELINE] Previous dry-run candidate invalidated.")
    except Exception as exc:
        raise RuntimeError(
            f"Could not invalidate previous dry-run candidate: {exc}"
        ) from exc


def _save_candidate(
    reference_dt,
    subject,
    plain,
    html,
    publish_ready,
    newsletters,
    ai,
):
    """Save the exact reviewed edition plus state-update metadata."""
    if not publish_ready:
        utils.log(
            "[PIPELINE] Dry-run candidate not saved because "
            "the edition is not publish ready."
        )
        return False

    source_ids = [
        source["id"]
        for source in newsletters.get("sources", [])
        if source.get("id")
    ]

    candidate = {
        "version": 1,
        "generated_at": reference_dt.isoformat(),
        "publish_ready": True,
        "subject": subject,
        "plain": plain,
        "html": html,
        "source_ids": source_ids,
        "top_headlines": ai.get("top_headlines", []),
        "consumed": False,
    }

    path = _candidate_path()

    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(
                candidate,
                handle,
                indent=2,
                ensure_ascii=False,
            )

        utils.log(
            "[PIPELINE] Sendable dry-run candidate saved: "
            f"{path}"
        )
        return True

    except Exception as exc:
        utils.log(
            f"[PIPELINE] Failed to save dry-run candidate: {exc}"
        )
        return False


def _load_valid_candidate(reference_dt):
    """Load a recent, publish-ready, unconsumed dry-run candidate."""
    path = _candidate_path()

    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as handle:
            candidate = json.load(handle)
    except Exception as exc:
        utils.log(
            f"[PIPELINE] Dry-run candidate could not be read: {exc}"
        )
        return None

    if not candidate.get("publish_ready"):
        utils.log(
            "[PIPELINE] Existing dry-run candidate is not publish ready; "
            "ignoring it."
        )
        return None

    if candidate.get("consumed"):
        utils.log(
            "[PIPELINE] Existing dry-run candidate was already consumed; "
            "ignoring it."
        )
        return None

    generated_at_raw = candidate.get("generated_at")

    try:
        generated_at = datetime.fromisoformat(generated_at_raw)
    except Exception:
        utils.log(
            "[PIPELINE] Existing dry-run candidate has an invalid timestamp; "
            "ignoring it."
        )
        return None

    max_age_hours = getattr(
        config,
        "DRY_RUN_CANDIDATE_MAX_AGE_HOURS",
        2,
    )

    age_seconds = (reference_dt - generated_at).total_seconds()

    if age_seconds < 0:
        utils.log(
            "[PIPELINE] Existing dry-run candidate has a future timestamp; "
            "ignoring it."
        )
        return None

    if age_seconds > max_age_hours * 3600:
        utils.log(
            "[PIPELINE] Existing dry-run candidate is too old "
            f"({age_seconds / 3600:.1f}h; max {max_age_hours}h); "
            "ignoring it."
        )
        return None

    required = (
        "subject",
        "plain",
        "html",
        "source_ids",
        "top_headlines",
    )

    missing = [
        key
        for key in required
        if key not in candidate
    ]

    if missing:
        utils.log(
            "[PIPELINE] Existing dry-run candidate is incomplete "
            f"(missing: {', '.join(missing)}); ignoring it."
        )
        return None

    return candidate


def _mark_candidate_consumed():
    """Mark a candidate as consumed after at least one accepted delivery."""
    path = _candidate_path()

    if not os.path.exists(path):
        return

    try:
        with open(path, "r", encoding="utf-8") as handle:
            candidate = json.load(handle)

        candidate["consumed"] = True

        with open(path, "w", encoding="utf-8") as handle:
            json.dump(
                candidate,
                handle,
                indent=2,
                ensure_ascii=False,
            )

        utils.log(
            "[PIPELINE] Dry-run candidate marked as consumed."
        )

    except Exception as exc:
        utils.log(
            "[PIPELINE] WARNING: broadcast succeeded but the dry-run "
            f"candidate could not be marked consumed: {exc}"
        )


def _broadcast_existing_candidate(reference_dt, candidate):
    """Send the exact HTML/plain-text edition produced by the dry run."""
    subject = candidate["subject"]
    plain = candidate["plain"]
    html = candidate["html"]

    generated_at = candidate.get("generated_at", "unknown")

    utils.log(
        "[PIPELINE] Valid dry-run candidate found."
    )
    utils.log(
        "[PIPELINE] Reusing exact reviewed edition generated at "
        f"{generated_at}."
    )
    utils.log(
        "[PIPELINE] Gmail, ranking, synthesis, and rendering skipped."
    )

    try:
        subscribers = subscriber_store.get_active_subscribers()

        utils.log(
            f"[BROADCAST] Active subscribers: "
            f"{len(subscribers)}."
        )

        delivery = broadcast_sender.deliver(
            subject,
            plain,
            html,
            subscribers,
        )

    except Exception as exc:
        utils.log(
            f"[BROADCAST] Delivery setup/send failed: {exc}"
        )

        delivery = {
            "attempted": 0,
            "accepted": 0,
            "failed": 0,
            "failures": [],
        }

    sent = delivery.get("accepted", 0) > 0

    if sent:
        utils.append_processed_ids(
            candidate.get("source_ids", [])
        )

        story_memory.remember(
            candidate.get("top_headlines", []),
            reference_dt,
        )

        utils.write_last_run(reference_dt)

        _mark_candidate_consumed()

        utils.log(
            "[PIPELINE] Broadcast accepted for "
            f"{delivery.get('accepted', 0)}/"
            f"{delivery.get('attempted', 0)} "
            "subscriber(s); state updated."
        )

        if delivery.get("failed", 0):
            utils.log(
                f"[PIPELINE] WARNING: "
                f"{delivery['failed']} recipient(s) failed; "
                "review Resend logs before the next edition."
            )

    else:
        utils.log(
            "[PIPELINE] No subscriber delivery was accepted; "
            "state NOT updated and candidate remains available."
        )

    return sent


def run(dry_run=False, force=False):
    utils.ensure_dirs()

    reference_dt = utils.now_local()

    utils.log("=" * 70)
    utils.log(f"[PIPELINE] Starting run at {reference_dt.isoformat()}")

    if not force and utils.recently_ran(reference_dt):
        utils.log("[PIPELINE] Ran recently; use --force to override.")
        return False

    # A new dry run supersedes any previously reviewed candidate.
    # Fail closed if the old candidate cannot be invalidated.
    if dry_run:
        try:
            _invalidate_candidate()
        except Exception as exc:
            utils.log(f"[PIPELINE] Dry run aborted: {exc}")
            utils.log("=" * 70)
            return False

    # ---------------------------------------------------------
    # LIVE CANDIDATE REUSE
    #
    # A live run first checks for a recent publish-ready dry-run
    # candidate. If one exists, send the exact reviewed artifact
    # instead of regenerating the edition and spending more AI calls.
    # ---------------------------------------------------------

    if not dry_run:
        candidate = _load_valid_candidate(reference_dt)

        if candidate:
            sent = _broadcast_existing_candidate(
                reference_dt,
                candidate,
            )

            utils.log("=" * 70)
            return sent

    start = utils.determine_fetch_start(reference_dt)
    utils.log(f"[PIPELINE] Newsletter window starts at {start.isoformat()}")

    # ---------------------------------------------------------
    # Market data
    # ---------------------------------------------------------

    try:
        market = market_data.get_all_market_data()
    except Exception as exc:
        utils.log(f"[PIPELINE] Market data failed: {exc}")
        market = {
            "equities": {},
            "fx": {},
            "rates": {},
            "data_ok": False,
        }

    # ---------------------------------------------------------
    # Gmail ingestion
    # ---------------------------------------------------------

    try:
        messages = gmail_client.fetch_messages_since(start)
    except Exception as exc:
        utils.log(f"[PIPELINE] Gmail fetch failed: {exc}")
        messages = []

    processed = utils.read_processed_ids()

    records = email_parser.parse_messages(
        [
            message
            for message in messages
            if message.get("id") not in processed
        ]
    )

    newsletters = newsletter_filter.filter_and_categorize(
        records,
        reference_dt,
    )

    # ---------------------------------------------------------
    # Story extraction / ranking
    # ---------------------------------------------------------

    package = story_ranker.build_ranked_package(
        newsletters,
        market,
        _recent_titles(reference_dt),
    )

    # Save a redacted ranking audit regardless of publication outcome.
    try:
        path = os.path.join(
            config.DEBUG_DIR,
            f"ranking_{reference_dt:%Y%m%d_%H%M%S}.json",
        )

        with open(path, "w", encoding="utf-8") as handle:
            json.dump(
                _redact(package),
                handle,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

        utils.log(f"[RANK] Audit saved: {path}")

    except Exception as exc:
        utils.log(f"[RANK] Audit save failed: {exc}")

    # ---------------------------------------------------------
    # PRE-SYNTHESIS PUBLICATION GATE
    #
    # If ranking already proves that there is not enough distinct
    # material for a legitimate edition, do not waste writer/editor
    # AI calls trying to manufacture one.
    # ---------------------------------------------------------

    rank_pass = bool(
        package.get("quality", {}).get("pass", True)
    )

    selected_clusters = package.get("headline_clusters") or []
    selected_count = len(selected_clusters)

    if (
        not rank_pass
        or selected_count < config.MIN_SELECTED_STORIES
    ):
        utils.log(
            "[PIPELINE] Ranking quality gate failed or there was "
            "insufficient distinct editorial material; synthesis skipped."
        )
        utils.log(
            f"[PIPELINE] Selected {selected_count} editorial cluster(s); "
            f"minimum required is {config.MIN_SELECTED_STORIES}."
        )
        utils.log(
            "[PIPELINE] State not updated and no newsletter was broadcast."
        )
        utils.log("=" * 70)
        return False

    # ---------------------------------------------------------
    # Cohesive synthesis
    # ---------------------------------------------------------

    ai = synthesis.synthesize(
        market,
        package,
        reference_dt,
    )

    synth_pass = bool(
        ai.get("quality", {}).get("pass")
    )

    publish_ready = bool(
        rank_pass
        and synth_pass
        and ai.get("top_headlines")
    )

    status = {
        "Relevant newsletters": newsletters
        .get("stats", {})
        .get("relevant_sources", 0),
        "Rank quality": rank_pass,
        "Synthesis quality": synth_pass,
        "Publish ready": publish_ready,
        "AI engine": ai.get("engine", "unknown"),
    }

    # ---------------------------------------------------------
    # Render exact Parallax artifact
    # ---------------------------------------------------------

    plain, html = brief_builder.build_brief(
        reference_dt,
        market,
        ai,
        status,
    )

    if not publish_ready:
        warning = (
            '<div style="max-width:600px;margin:0 auto 12px;'
            'padding:10px;background:#fff3cd;color:#664d03;'
            'font-family:Arial,Helvetica,sans-serif;font-size:12px;'
            'text-align:center;">'
            '<strong>INTERNAL REVIEW WARNING:</strong> '
            'This edition did not pass the automated quality gate. '
            'Do not publish without manual review.'
            '</div>'
        )

        html = warning + html

        plain = (
            "INTERNAL REVIEW WARNING: QUALITY GATE FAILED.\n\n"
            + plain
        )

    subject = ai.get(
        "daily_title",
        config.EMAIL_SUBJECT_PREFIX,
    ).strip()

    # Always retain a generated edition locally once synthesis occurred.
    email_sender.save_local(
        subject,
        plain,
        html,
    )

    # ---------------------------------------------------------
    # Dry run
    # ---------------------------------------------------------

    if dry_run:
        if publish_ready:
            _save_candidate(
                reference_dt,
                subject,
                plain,
                html,
                publish_ready,
                newsletters,
                ai,
            )

        utils.log(
            "[PIPELINE] Dry run: state not updated. "
            f"Publish ready: {publish_ready}."
        )

        sent = False

    # ---------------------------------------------------------
    # Failed quality gate
    # ---------------------------------------------------------

    elif not publish_ready:
        utils.log(
            "[PIPELINE] LIVE DELIVERY BLOCKED: "
            "quality gate failed. State not updated."
        )

        sent = False

    # ---------------------------------------------------------
    # Production broadcast
    # ---------------------------------------------------------

    else:
        try:
            subscribers = subscriber_store.get_active_subscribers()

            utils.log(
                f"[BROADCAST] Active subscribers: "
                f"{len(subscribers)}."
            )

            delivery = broadcast_sender.deliver(
                subject,
                plain,
                html,
                subscribers,
            )

        except Exception as exc:
            utils.log(
                f"[BROADCAST] Delivery setup/send failed: {exc}"
            )

            delivery = {
                "attempted": 0,
                "accepted": 0,
                "failed": 0,
                "failures": [],
            }

        sent = delivery.get("accepted", 0) > 0

        if sent:
            # The edition was distributed to at least one active
            # subscriber. Partial recipient failures do not cause
            # successful recipients to receive the same edition again.
            ids = [
                source["id"]
                for source in newsletters.get("sources", [])
                if source.get("id")
            ]

            utils.append_processed_ids(ids)

            story_memory.remember(
                ai.get("top_headlines", []),
                reference_dt,
            )

            utils.write_last_run(reference_dt)

            utils.log(
                "[PIPELINE] Broadcast accepted for "
                f"{delivery.get('accepted', 0)}/"
                f"{delivery.get('attempted', 0)} "
                "subscriber(s); state updated."
            )

            if delivery.get("failed", 0):
                utils.log(
                    f"[PIPELINE] WARNING: "
                    f"{delivery['failed']} recipient(s) failed; "
                    "review Resend logs before the next edition."
                )

        else:
            utils.log(
                "[PIPELINE] No subscriber delivery was accepted; "
                "state NOT updated."
            )

    utils.log("=" * 70)

    return sent


def parse_args(argv):
    return (
        "--dry-run" in argv,
        "--force" in argv,
    )


if __name__ == "__main__":
    dry, force = parse_args(sys.argv[1:])
    run(dry, force)