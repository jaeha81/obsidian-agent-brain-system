import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import chatgpt_daily_collector as collector


class ChatGPTDailyCollectorTests(unittest.TestCase):
    def test_validate_capture_rejects_404_overview(self):
        capture = {
            "href": "https://chatgpt.com/pulse",
            "title": "ChatGPT",
            "overviewText": "404 Not Found",
            "cards": [],
            "bodyStart": "404 Not Found",
        }

        with self.assertRaisesRegex(RuntimeError, "404"):
            collector.validate_capture_for_note(capture)

    def test_validate_capture_rejects_zero_cards(self):
        capture = {
            "href": "https://chatgpt.com/pulse",
            "title": "ChatGPT Pulse",
            "overviewText": "Pulse\n오늘의 플러스 요약",
            "cards": [],
            "bodyStart": "Pulse",
        }

        with self.assertRaisesRegex(RuntimeError, "No Pulse cards"):
            collector.validate_capture_for_note(capture)

    def test_validate_capture_accepts_pulse_with_cards(self):
        capture = {
            "href": "https://chatgpt.com/pulse",
            "title": "ChatGPT Pulse",
            "overviewText": "Pulse\n오늘의 플러스 요약",
            "cards": [{"title": "Card 1", "summary": "Summary", "detailText": "Detail"}],
            "bodyStart": "Pulse",
        }

        collector.validate_capture_for_note(capture)

    def test_build_recovery_capture_preserves_source_error_and_cards(self):
        capture = collector.build_recovery_capture("ChatGPT Pulse returned a 404 or not-found page.")

        self.assertEqual(capture["collectionStatus"], "fallback")
        self.assertIn("404", capture["sourceError"])
        self.assertGreaterEqual(len(capture["cards"]), 3)
        self.assertIn("OABS", capture["overviewText"])
        collector.validate_capture_for_note(capture)


if __name__ == "__main__":
    unittest.main()
