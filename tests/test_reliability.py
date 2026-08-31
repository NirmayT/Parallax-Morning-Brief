import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

import config
import story_ranker
import synthesis


class _FakeCompletions:
    def __init__(self, response):
        self.response = response

    def create(self, **kwargs):
        return self.response


class _FakeClient:
    def __init__(self, response):
        self.chat = SimpleNamespace(completions=_FakeCompletions(response))




class _FlakyCompletions:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("429 GenerateRequestsPerMinute limit. Please retry in 2s")
        return self.response


class _FlakyClient:
    def __init__(self, response):
        self.completions = _FlakyCompletions(response)
        self.chat = SimpleNamespace(completions=self.completions)


class ReliabilityTests(unittest.TestCase):
    def test_sentence_count_masks_us_abbreviation(self):
        text = "U.S. yields rose. Stocks held firm. The dollar was mixed."
        self.assertEqual(synthesis._sentence_count(text), 3)

    def test_synthesis_call_rejects_length_finish(self):
        response = SimpleNamespace(
            choices=[SimpleNamespace(
                finish_reason="length",
                message=SimpleNamespace(content="BEGIN BRIEF\nTITLE: partial"),
            )],
            usage=SimpleNamespace(prompt_tokens=100, completion_tokens=50),
        )
        with self.assertRaisesRegex(RuntimeError, "truncated"):
            synthesis._call(_FakeClient(response), "system", "user", max_tokens=100)

    def test_synthesis_call_retries_rpm_limit_once(self):
        config._AI_LAST_CALL_TIME = 0.0
        config._AI_DAILY_QUOTA_EXHAUSTED = False
        response = SimpleNamespace(
            choices=[SimpleNamespace(
                finish_reason="stop",
                message=SimpleNamespace(content="complete"),
            )],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
        )
        client = _FlakyClient(response)
        with patch.object(synthesis.time, "sleep") as sleep:
            result = synthesis._call(client, "system", "user", max_tokens=100)
        self.assertEqual(result, "complete")
        self.assertEqual(client.completions.calls, 2)
        sleep.assert_called_once()

    def test_extraction_recovers_missing_input_before_fallback(self):
        theme = config.THEME_ORDER[0]
        newsletters = {
            "by_theme": {
                theme: [{
                    "source": "Axios Markets",
                    "subject": "Rates move",
                    "paragraph": "U.S. Treasury yields rose after the latest market repricing.",
                    "freshness": "today",
                }]
            }
        }
        malformed = "SUMMARY: Treasury yields rose.\nEVIDENCE: U.S. Treasury yields rose after the latest market repricing."
        repaired = """STORY
INPUT: N1
HEADLINE: Treasury yields rise
SUMMARY: Treasury yields rose after market repricing.
EVIDENCE: U.S. Treasury yields rose after the latest market repricing.
THEMES: rates and central banks
ASSETS: rates
ENTITIES: none
CATALYST: none
END"""

        with patch.object(story_ranker, "_text_call", side_effect=[malformed, repaired]):
            stories, metrics = story_ranker.extract_stories(newsletters, client=object())

        self.assertEqual(metrics["fallback_inputs"], 0)
        self.assertEqual(metrics["parsed_inputs"], 1)
        self.assertTrue(metrics["quality_pass"])
        self.assertEqual(stories[0].extraction_method, "ai_labeled_text")


if __name__ == "__main__":
    unittest.main()
