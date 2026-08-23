"""Server-side subscriber access.

This module uses a Supabase secret key and must never be imported into browser code.
The secret key bypasses Row Level Security by design, so keep it only in local/server
environment variables.
"""
from __future__ import annotations

import re
from typing import Any

import config

try:
    from supabase import Client, create_client
    SUPABASE_AVAILABLE = True
except Exception:
    Client = Any
    SUPABASE_AVAILABLE = False


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _client() -> Client:
    if not SUPABASE_AVAILABLE:
        raise RuntimeError("supabase package is not installed")
    if not config.SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL is not configured")
    if not config.SUPABASE_SECRET_KEY:
        raise RuntimeError("SUPABASE_SECRET_KEY is not configured")
    return create_client(config.SUPABASE_URL, config.SUPABASE_SECRET_KEY)


def get_active_subscribers(client=None) -> list[dict]:
    """Return active subscribers needed for individualized newsletter delivery."""
    client = client or _client()
    response = (
        client.table("subscribers")
        .select("id,email,unsubscribe_token")
        .eq("status", "active")
        .order("subscribed_at")
        .execute()
    )

    rows = getattr(response, "data", None) or []
    output = []
    seen = set()

    for row in rows:
        email = str(row.get("email") or "").strip().lower()
        token = str(row.get("unsubscribe_token") or "").strip()
        if not _EMAIL_RE.match(email) or not token or email in seen:
            continue
        seen.add(email)
        output.append({
            "id": str(row.get("id") or ""),
            "email": email,
            "unsubscribe_token": token,
        })

    return output
