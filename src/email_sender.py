"""Local edition artifact storage.

Production subscriber delivery is handled exclusively by broadcast_sender.py
through Resend. This module intentionally contains no email-send path.
"""
from __future__ import annotations

import os

import config
import utils


def save_local(subject: str, plain: str, html: str) -> str:
    """Save the rendered edition locally and return the HTML file path."""
    utils.ensure_dirs()

    stamp = utils.now_local().strftime("%Y%m%d_%H%M%S")
    html_path = os.path.join(config.OUTPUT_DIR, f"brief_{stamp}.html")
    txt_path = os.path.join(config.OUTPUT_DIR, f"brief_{stamp}.txt")

    with open(html_path, "w", encoding="utf-8") as handle:
        handle.write(html)

    with open(txt_path, "w", encoding="utf-8") as handle:
        handle.write(plain)

    utils.log(f"[SENDER] Saved local copy: {html_path}")
    return html_path