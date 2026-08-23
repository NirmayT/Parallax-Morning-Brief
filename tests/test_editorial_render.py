import os
import unittest
from datetime import datetime

from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

import brief_builder
import brief_sections


class EditorialRenderTests(unittest.TestCase):
    def test_market_read_does_not_render_per_asset_recap(self):
        ai = {
            "daily_title": "Rates Set the Test",
            "sentiment": "Mixed",
            "mood": "Stocks stabilized as yields stayed firm.",
            "key_line": "The rebound still has to coexist with higher discount rates.",
            "market_summary": {
                "overview": "Equities held up while yields rose, leaving a mixed cross-asset signal.",
                "movements": [],
            },
            "parallax": {"title": "Rates versus resilience", "text": "One. Two. Three."},
            "top_headlines": [],
            "whats_moving": {"story": "", "watch": []},
            "open_question": {"question": "What changes the view?", "answer": "One. Two. Three."},
        }
        market = {
            "equities": {"S&P 500": {"latest": 100.0, "prev": 99.0, "ret_1d": 0.01, "decimals": 2}},
            "fx": {},
            "rates": {},
        }
        html = brief_builder.build_html(datetime(2026, 8, 22), market, ai, {})
        self.assertIn("Market read", html)
        self.assertIn("Equities", html)  # snapshot table remains
        self.assertNotIn("<b>Stocks.</b>", html)
        self.assertNotIn("<b>Currencies.</b>", html)
        self.assertNotIn("<b>Bonds.</b>", html)

    def test_empty_whats_moving_is_omitted(self):
        self.assertEqual(brief_sections.html_moving({"story": "", "watch": []}), "")
        self.assertEqual(brief_sections.txt_moving({"story": "", "watch": []}), "")


if __name__ == "__main__":
    unittest.main()
