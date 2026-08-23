"""Core offline regression checks.

Run with:
    py -m unittest discover -s tests
"""
import os
import unittest

from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

import story_ranker
import brief_builder

# Regression tests must remain deterministic and must never consume Gemini
# quota. cluster_stories() will therefore use only its Python clustering path.
story_ranker._client = lambda: None


class RankingTests(unittest.TestCase):
    def _story(
        self,
        ident,
        headline,
        source,
        entities=None,
        assets=None,
        freshness="today",
    ):
        return story_ranker.Story(
            ident,
            headline,
            headline,
            headline,
            source,
            freshness,
            ["rates"],
            assets or ["rates"],
            entities or [],
            "",
            False,
        )

    def test_same_fed_story_clusters(self):
        stories = [
            self._story(
                "1",
                "Markets price fewer Fed cuts",
                "Axios",
                ["Federal Reserve"],
                ["rates", "fx"],
            ),
            self._story(
                "2",
                "Rate cut expectations move outward",
                "Yahoo",
                ["Federal Reserve"],
                ["rates", "equities"],
            ),
        ]

        clusters, metadata = story_ranker.cluster_stories(
            stories,
            client=None,
        )

        self.assertEqual(len(clusters), 1)
        self.assertIn("borderline_complete", metadata)

    def test_different_central_banks_remain_separate(self):
        stories = [
            self._story(
                "1",
                "Federal Reserve delays rate cuts",
                "Axios",
                ["Federal Reserve"],
            ),
            self._story(
                "2",
                "Bank of Canada delays rate cuts",
                "Yahoo",
                ["Bank of Canada"],
            ),
        ]

        clusters, metadata = story_ranker.cluster_stories(
            stories,
            client=None,
        )

        self.assertEqual(len(clusters), 2)
        self.assertIn("borderline_complete", metadata)

    def test_rate_format_is_not_divided(self):
        rows = brief_builder._rows(
            {
                "US 10Y": {
                    "latest": 4.696,
                    "prev": 4.653,
                }
            },
            rate=True,
        )

        self.assertEqual(rows[0][1], "4.70%")
        self.assertEqual(rows[0][2], "+4")

    def test_fx_is_neutral_color(self):
        rows = brief_builder._rows(
            {
                "USD/CAD": {
                    "latest": 1.38,
                    "prev": 1.37,
                    "ret_1d": 0.01,
                    "decimals": 4,
                }
            },
            neutral=True,
        )

        self.assertEqual(rows[0][3], brief_builder.MUTE)


if __name__ == "__main__":
    unittest.main()
