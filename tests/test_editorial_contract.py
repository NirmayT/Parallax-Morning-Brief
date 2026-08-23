import os
import unittest
from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

import brief_sections
import story_ranker
import synthesis


class EditorialContractTests(unittest.TestCase):
    def _package(self):
        return {
            "lead_story": {"cluster_id": "C1", "canonical_story": "Bond yields rise as consumer pressure persists"},
            "headline_clusters": [
                {"cluster_id": "C1", "sources": ["Yahoo Finance"], "evidence": ["Yields rose and consumer pressure persisted."]},
                {"cluster_id": "C2", "sources": ["Torsten Slok"], "evidence": ["Unemployment continued to decline."]},
            ],
            "watch_items": [],
        }

    def _draft(self):
        return """BEGIN BRIEF
TITLE:
Two Economies, One Market
RISK MOOD:
Mixed
OPENING:
Markets are balancing resilient risk appetite against uneven household conditions.
KEY LINE:
The same economy can look strong in asset prices and fragile in household budgets.
MARKET READ:
Equities held firm while Treasury yields stayed elevated. That combination keeps financial conditions important even without a broad risk-off move.
PARALLAX TITLE:
Markets versus households
PARALLAX:
Higher yields and uneven consumer conditions point to different pressures inside the same economy. Asset prices can remain resilient even when some households face tighter budgets. That gap matters because broad spending strength may hide very different experiences across income groups.
HEADLINE 1 CLUSTER:
C1
HEADLINE 1:
Consumer pressure meets higher yields
HEADLINE 1 SUMMARY:
Treasury yields remained elevated while company commentary pointed to uneven household conditions. The combination matters because borrowing costs do not affect every consumer equally.
HEADLINE 1 SOURCES:
Yahoo Finance
HEADLINE 2 CLUSTER:
C2
HEADLINE 2:
Asian unemployment keeps improving
HEADLINE 2 SUMMARY:
Unemployment continued to decline in the selected labor-market evidence. That provides a useful counterpoint to concerns about broad employment weakness.
HEADLINE 2 SOURCES:
Torsten Slok
WHAT'S MOVING:
none
WATCH 1:
none
WATCH 2:
none
WATCH 3:
none
WATCH 4:
none
OPEN QUESTION:
Why can higher interest rates hurt some consumers more than others?
OPEN ANSWER:
Higher rates raise borrowing costs, which takes a larger bite out of budgets for households that rely more on debt. That can reduce spending because more income goes toward interest payments instead of goods and services. In an interview, watch consumer spending, delinquencies, and company comments for signs that the pressure is spreading.
END BRIEF"""

    def test_reordered_clusters_validate_by_id_not_position(self):
        raw = self._draft().replace(
            "HEADLINE 1 CLUSTER:\nC1\nHEADLINE 1:\nConsumer pressure meets higher yields\nHEADLINE 1 SUMMARY:\nTreasury yields remained elevated while company commentary pointed to uneven household conditions. The combination matters because borrowing costs do not affect every consumer equally.\nHEADLINE 1 SOURCES:\nYahoo Finance\nHEADLINE 2 CLUSTER:\nC2\nHEADLINE 2:\nAsian unemployment keeps improving\nHEADLINE 2 SUMMARY:\nUnemployment continued to decline in the selected labor-market evidence. That provides a useful counterpoint to concerns about broad employment weakness.\nHEADLINE 2 SOURCES:\nTorsten Slok",
            "HEADLINE 1 CLUSTER:\nC2\nHEADLINE 1:\nAsian unemployment keeps improving\nHEADLINE 1 SUMMARY:\nUnemployment continued to decline in the selected labor-market evidence. That provides a useful counterpoint to concerns about broad employment weakness.\nHEADLINE 1 SOURCES:\nTorsten Slok\nHEADLINE 2 CLUSTER:\nC1\nHEADLINE 2:\nConsumer pressure meets higher yields\nHEADLINE 2 SUMMARY:\nTreasury yields remained elevated while company commentary pointed to uneven household conditions. The combination matters because borrowing costs do not affect every consumer equally.\nHEADLINE 2 SOURCES:\nYahoo Finance",
        )
        result = synthesis._parse_to_result(raw, self._package())
        self.assertEqual([x["cluster_id"] for x in result["top_headlines"]], ["C2", "C1"])

    def test_recap_title_is_rejected(self):
        bad = self._draft().replace("Two Economies, One Market", "Stocks Rise as Yields Fall")
        with self.assertRaisesRegex(ValueError, "market recap"):
            synthesis._parse_to_result(bad, self._package())

    def test_open_question_is_short_interview_style(self):
        result = synthesis._parse_to_result(self._draft(), self._package())
        self.assertTrue(result["open_question"]["question"].startswith("Why"))

    def test_generic_fallback_sections_are_omitted(self):
        self.assertEqual(brief_sections.html_parallax({"title": "", "text": ""}), "")
        self.assertEqual(brief_sections.html_question({"question": "", "answer": ""}), "")

    def test_promo_story_is_non_editorial(self):
        story = story_ranker.Story(
            "1", "FXStreet trading cashback", "Cashback is available on trades.",
            "Users can receive cashback and customer support.", "FXStreet Traders", "today",
            ["foreign exchange"], ["fx"], [], "", False, "ai_labeled_text", True,
        )
        self.assertFalse(story_ranker._is_editorial_story(story))

    def test_same_source_ai_labor_variants_cluster(self):
        a = story_ranker.Story(
            "1", "AI job disruption absent in outsourcing hubs",
            "AI employment disruption has not appeared in major outsourcing centers.",
            "AI employment disruption has not appeared in major outsourcing centers.",
            "Torsten Slok", "today", ["ai", "employment", "outsourcing"], ["macro"], [], "", False,
        )
        b = story_ranker.Story(
            "2", "White collar AI displacement absent in BPO nations",
            "Large scale AI job displacement has not materialized in outsourcing markets.",
            "Large scale AI job displacement has not materialized in outsourcing markets.",
            "Torsten Slok", "today", ["ai", "labor market", "outsourcing"], ["macro"], [], "", False,
        )
        clusters, _ = story_ranker.cluster_stories([a, b], client=None)
        self.assertEqual(len(clusters), 1)

    def test_non_editorial_extraction_is_not_reintroduced_as_fallback(self):
        theme = story_ranker.config.THEME_ORDER[2]
        newsletters = {
            "by_theme": {
                theme: [{
                    "source": "FXStreet Traders",
                    "subject": "Trading cashback",
                    "paragraph": "Users can receive cashback on trades and contact customer support.",
                    "freshness": "today",
                }]
            }
        }
        response = """STORY
INPUT: N1
HEADLINE: FXStreet trading cashback
SUMMARY: Users can receive cashback on trades.
EVIDENCE: Users can receive cashback on trades and contact customer support.
THEMES: foreign exchange
ASSETS: fx
ENTITIES: FXStreet
CATALYST: none
EDITORIAL: no
END"""
        from unittest.mock import patch
        with patch.object(story_ranker, "_text_call", return_value=response):
            stories, metrics = story_ranker.extract_stories(newsletters, client=object())
        self.assertEqual(stories, [])
        self.assertEqual(metrics["fallback_inputs"], 0)
        self.assertEqual(metrics["non_editorial_inputs"], 1)


if __name__ == "__main__":
    unittest.main()
