import os
import unittest

from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

import synthesis


class CohesiveParserTests(unittest.TestCase):
    def package(self):
        return {
            "lead_story": {"cluster_id": "C1", "canonical_story": "Markets reduce expected cuts"},
            "headline_clusters": [
                {
                    "cluster_id": "C1",
                    "sources": ["Axios Markets"],
                    "evidence": ["Treasury yields rose while equities held firm."],
                }
            ],
            "watch_items": ["Friday inflation report"],
        }

    def valid(self):
        return """BEGIN BRIEF
TITLE:
Rates Reset the Tone
RISK MOOD:
Cautious
OPENING:
Markets are balancing firmer equities against higher yields.
KEY LINE:
Rates remain the clearest test of the rebound.
MARKET READ:
Equities held up while Treasury yields rose. That mix leaves risk appetite intact but the discount-rate backdrop less forgiving.
PARALLAX TITLE:
Growth and rates
PARALLAX:
Yields rose while stocks held up. That divergence suggests investors have not treated the rate move as a decisive growth warning. A sharper yield increase would test that balance.
HEADLINE 1 CLUSTER:
C1
HEADLINE 1:
Markets reduce expected cuts
HEADLINE 1 SUMMARY:
Investors shifted rate expectations as Treasury yields moved higher. The change matters because higher discount rates can make an equity rebound harder to sustain.
HEADLINE 1 SOURCES:
Axios Markets
WHAT'S MOVING:
none
WATCH 1:
Friday inflation report
WATCH 2:
none
WATCH 3:
none
WATCH 4:
none
OPEN QUESTION:
Can growth hold up as rates stay elevated?
OPEN ANSWER:
The current evidence still points to resilience. Friday inflation data is the next approved test. A renewed yield surge alongside weaker equities would challenge that view.
END BRIEF"""

    def test_multiline_template_parses(self):
        result = synthesis._parse_to_result(self.valid(), self.package())
        self.assertEqual(result["daily_title"], "Rates Reset the Tone")
        self.assertEqual(result["whats_moving"]["watch"], ["Friday inflation report"])
        self.assertEqual(result["whats_moving"]["story"], "")
        self.assertEqual(result["market_summary"]["movements"], [])
        self.assertIn("Equities held up", result["market_summary"]["overview"])

    def test_missing_end_is_rejected(self):
        with self.assertRaises(ValueError):
            synthesis._parse_to_result(self.valid().replace("END BRIEF", ""), self.package())

    def test_unapproved_source_is_rejected(self):
        with self.assertRaises(ValueError):
            synthesis._parse_to_result(
                self.valid().replace("Axios Markets\nWHAT'S", "Unknown Source\nWHAT'S"),
                self.package(),
            )

    def test_cluster_context_includes_evidence(self):
        text = synthesis._cluster_text({
            "cluster_id": "C1",
            "canonical_story": "Rates rise",
            "summary": "Treasury yields moved higher.",
            "evidence": ["The 10-year Treasury yield rose four basis points."],
            "sources": ["Axios Markets"],
            "assets": ["rates"],
            "catalysts": [],
        })
        self.assertIn("EVIDENCE 1: The 10-year Treasury yield rose four basis points.", text)

    def test_opening_must_be_one_sentence(self):
        invalid = self.valid().replace(
            "Markets are balancing firmer equities against higher yields.",
            "Markets are firmer. Yields are higher.",
        )
        with self.assertRaisesRegex(ValueError, "OPENING must contain exactly one sentence"):
            synthesis._parse_to_result(invalid, self.package())


if __name__ == "__main__":
    unittest.main()
