"""Convert Gmail MIME payloads into bounded, cleaned newsletter records."""
import base64
import re
from email.utils import parseaddr, parsedate_to_datetime
import config
import utils
from bs4 import BeautifulSoup

_URL_RE = re.compile(r"https?://\S+")


def _decode(value):
    try:
        return base64.urlsafe_b64decode(value.encode()).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _parts(payload):
    if payload.get("body", {}).get("data"):
        yield payload.get("mimeType", ""), _decode(payload["body"]["data"])
    for part in payload.get("parts", []) or []:
        yield from _parts(part)


def _header(headers, name):
    return next((item.get("value", "") for item in headers if item.get("name", "").lower() == name.lower()), "")


def _paragraphs(text):
    bad = ("unsubscribe", "manage preferences", "view in browser", "privacy policy")
    blocks = []
    for block in text.replace("\r", "").split("\n\n"):
        joined = " ".join(block.split())
        stripped = re.sub(r"\s{2,}", " ", _URL_RE.sub("", joined)).strip()
        if len(stripped) < 35 or any(term in stripped.lower() for term in bad):
            continue
        blocks.append(stripped[:config.MAX_CHARS_PER_PARAGRAPH])
    return blocks[:config.MAX_PARAGRAPHS_PER_SOURCE]


def parse_message(message):
    payload, headers = message.get("payload", {}), message.get("payload", {}).get("headers", [])
    plain, html = [], []
    for mime, text in _parts(payload):
        (plain if mime == "text/plain" else html if mime == "text/html" else []).append(text)
    body = "\n\n".join(plain)
    if not body and html:
        soup = BeautifulSoup("\n".join(html), "lxml")
        for tag in soup(["script", "style", "head"]):
            tag.decompose()
        body = soup.get_text("\n\n")
    sender_name, sender_mail = parseaddr(_header(headers, "From"))
    try:
        received = parsedate_to_datetime(_header(headers, "Date")).astimezone(config.TIMEZONE)
    except Exception:
        received = None
    return {
        "id": message.get("id"), "sender_name": sender_name or sender_mail or "Unknown",
        "sender_email": sender_mail, "subject": _header(headers, "Subject") or "(no subject)",
        "received": received, "paragraphs": _paragraphs(body),
    }


def parse_messages(messages):
    return [record for record in (parse_message(message) for message in messages) if record["paragraphs"]]