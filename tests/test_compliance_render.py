import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

import brief_builder
import brief_sections
import broadcast_sender


class ComplianceRenderTests(unittest.TestCase):
    def _ai(self):
        return {
            "daily_title": "Two Economies, One Market",
            "sentiment": "Mixed",
            "mood": "Markets opened with competing signals.",
            "key_line": "The divergence matters more than the headline move.",
            "market_summary": {"overview": "Equities held up while rates eased."},
            "parallax": {"title": "Two angles", "text": "One. Two. Three."},
            "top_headlines": [],
            "whats_moving": {
                "story": "",
                "watch": ["earnings reports before the market open"],
            },
            "open_question": {
                "question": "Why do rates matter for stocks?",
                "answer": "One. Two. Three.",
            },
        }

    def test_watch_items_are_sentence_cased(self):
        html = brief_sections.html_moving(
            {"story": "", "watch": ["earnings reports before the market open"]}
        )
        self.assertIn("Earnings reports before the market open", html)

    def test_html_footer_contains_identification_and_reason(self):
        with (
            patch.object(brief_builder.config, "PUBLISHER_NAME", "Parallax Research Group"),
            patch.object(brief_builder.config, "COMPLIANCE_CONTACT_EMAIL", "newsletter@parallaxresearchgroup.ca"),
            patch.object(brief_builder.config, "PUBLIC_SITE_URL", "https://parallaxresearchgroup.ca"),
            patch.object(
                brief_builder.config,
                "SUBSCRIPTION_DISCLOSURE",
                "You are receiving this email because you subscribed to the Parallax Morning Brief at parallaxresearchgroup.ca.",
            ),
        ):
            html = brief_builder.build_html(datetime(2026, 8, 27), {}, self._ai(), {})

        self.assertIn("Parallax Research Group", html)
        self.assertIn("newsletter@parallaxresearchgroup.ca", html)
        self.assertIn("because you subscribed", html)
        self.assertIn("data-parallax-unsubscribe", html)

    def test_live_sender_blocks_missing_contact_email(self):
        with (
            patch.object(broadcast_sender, "RESEND_AVAILABLE", True),
            patch.object(broadcast_sender.config, "RESEND_API_KEY", "test"),
            patch.object(broadcast_sender.config, "RESEND_FROM_EMAIL", "test@example.com"),
            patch.object(broadcast_sender.config, "PUBLIC_SITE_URL", "https://example.com"),
            patch.object(broadcast_sender.config, "PUBLISHER_NAME", "Parallax Research Group"),
            patch.object(broadcast_sender.config, "COMPLIANCE_CONTACT_EMAIL", ""),
            patch.object(broadcast_sender.config, "SUBSCRIPTION_DISCLOSURE", "You subscribed."),
        ):
            with self.assertRaises(RuntimeError):
                broadcast_sender._require_config()


if __name__ == "__main__":
    unittest.main()
