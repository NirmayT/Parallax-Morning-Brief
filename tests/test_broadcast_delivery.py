import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

import broadcast_sender


class BroadcastDeliveryTests(unittest.TestCase):
    def test_personalize_html_replaces_marker_once(self):
        html = "<div>Hello<br><span data-parallax-unsubscribe></span></div>"
        out = broadcast_sender.personalize_html(
            html, "https://example.com/unsubscribe?token=abc"
        )
        self.assertIn("Unsubscribe</a>", out)
        self.assertNotIn("data-parallax-unsubscribe", out)

    def test_personalize_html_requires_marker(self):
        with self.assertRaises(ValueError):
            broadcast_sender.personalize_html(
                "<div>Hello</div>",
                "https://example.com/unsubscribe?token=abc",
            )

    def test_unsubscribe_url_encodes_token(self):
        with patch.object(
            broadcast_sender.config,
            "PUBLIC_SITE_URL",
            "https://example.com",
        ):
            url = broadcast_sender.unsubscribe_url("a/b c")
        self.assertEqual(
            url,
            "https://example.com/unsubscribe?token=a%2Fb%20c",
        )


if __name__ == "__main__":
    unittest.main()
