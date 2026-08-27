"""Exact-HTML subscriber delivery through Resend."""
from __future__ import annotations

from urllib.parse import quote

import config
import utils

try:
    import resend
    RESEND_AVAILABLE = True
except Exception:
    resend = None
    RESEND_AVAILABLE = False


UNSUBSCRIBE_MARKER = '<span data-parallax-unsubscribe></span>'


def _require_config():
    if not RESEND_AVAILABLE:
        raise RuntimeError("resend package is not installed")
    if not config.RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY is not configured")
    if not config.RESEND_FROM_EMAIL:
        raise RuntimeError("RESEND_FROM_EMAIL is not configured")
    if not config.PUBLIC_SITE_URL:
        raise RuntimeError("PUBLIC_SITE_URL is not configured")

    # Fail closed on bulk-mail identification requirements.
    if not config.PUBLISHER_NAME:
        raise RuntimeError("PUBLISHER_NAME is not configured")
    if not config.COMPLIANCE_CONTACT_EMAIL:
        raise RuntimeError("COMPLIANCE_CONTACT_EMAIL is not configured")
    if not config.SUBSCRIPTION_DISCLOSURE:
        raise RuntimeError("SUBSCRIPTION_DISCLOSURE is not configured")


def unsubscribe_url(token: str) -> str:
    token = str(token or "").strip()
    if not token:
        raise ValueError("subscriber is missing unsubscribe_token")
    return f"{config.PUBLIC_SITE_URL}/unsubscribe?token={quote(token, safe='')}"


def personalize_html(html: str, url: str) -> str:
    """Insert a subscriber-specific unsubscribe link without changing the layout."""
    if UNSUBSCRIBE_MARKER not in html:
        raise ValueError("newsletter HTML is missing the unsubscribe marker")
    link = (
        '<a href="' + url + '" '
        'style="color:#6b7280;text-decoration:underline;">Unsubscribe</a>'
    )
    return html.replace(UNSUBSCRIBE_MARKER, link, 1)


def personalize_plain(plain: str, url: str) -> str:
    return (plain.rstrip() + f"\n\nUnsubscribe: {url}\n").strip() + "\n"


def _response_id(response) -> str:
    if isinstance(response, dict):
        return str(response.get("id") or "")
    return str(getattr(response, "id", "") or "")


def deliver(subject: str, plain: str, html: str, subscribers: list[dict]) -> dict:
    """Send one private, personalized copy to each active subscriber."""
    _require_config()

    count = len(subscribers)
    if count == 0:
        return {"attempted": 0, "accepted": 0, "failed": 0, "failures": []}

    if count > config.BROADCAST_MAX_RECIPIENTS:
        raise RuntimeError(
            f"Refusing to send to {count} subscribers; "
            f"BROADCAST_MAX_RECIPIENTS={config.BROADCAST_MAX_RECIPIENTS}"
        )

    resend.api_key = config.RESEND_API_KEY
    accepted = 0
    failures = []

    for subscriber in subscribers:
        email = str(subscriber.get("email") or "").strip().lower()
        token = str(subscriber.get("unsubscribe_token") or "").strip()

        try:
            url = unsubscribe_url(token)
            personalized_html = personalize_html(html, url)
            personalized_plain = personalize_plain(plain, url)

            params = {
                "from": config.RESEND_FROM_EMAIL,
                "to": [email],
                "subject": subject,
                "html": personalized_html,
                "text": personalized_plain,
                "headers": {
                    "List-Unsubscribe": f"<{url}>",
                    "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
                },
            }

            if config.RESEND_REPLY_TO:
                params["reply_to"] = config.RESEND_REPLY_TO

            response = resend.Emails.send(params)
            accepted += 1
            utils.log(
                f"[BROADCAST] Accepted recipient {accepted}/{count}; "
                f"provider_id={_response_id(response) or 'n/a'}"
            )

        except Exception as exc:
            failures.append(
                {
                    "subscriber_id": str(subscriber.get("id") or ""),
                    "error": str(exc),
                }
            )
            utils.log(
                f"[BROADCAST] Recipient failed "
                f"({len(failures)} failure(s) so far): {exc}"
            )

    return {
        "attempted": count,
        "accepted": accepted,
        "failed": len(failures),
        "failures": failures,
    }
