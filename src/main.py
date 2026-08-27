"""Parallax orchestration with cohesive-synthesis publication gate."""
import json
import os
import sys

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


def run(dry_run=False, force=False):
    utils.ensure_dirs()

    reference_dt = utils.now_local()

    utils.log("=" * 70)
    utils.log(f"[PIPELINE] Starting run at {reference_dt.isoformat()}")

    if not force and utils.recently_ran(reference_dt):
        utils.log("[PIPELINE] Ran recently; use --force to override.")
        return False

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
            "[PIPELINE] Insufficient distinct editorial material; "
            "synthesis skipped."
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