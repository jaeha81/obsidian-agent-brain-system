import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import chatgpt_daily_collector as collector


class ChatGPTDailyCollectorTests(unittest.TestCase):
    def test_build_note_includes_korean_summary_when_available(self):
        capture = {
            "overviewText": "English overview",
            "overviewKo": "한국어 개요",
            "cards": [
                {
                    "title": "Card 1",
                    "summary": "English summary",
                    "summaryKo": "한국어 요약",
                    "detailText": "English detail",
                    "detailKo": "한국어 상세",
                }
            ],
        }

        note = collector.build_note(capture, collector.date(2026, 6, 6))

        self.assertIn("## Overview (KO)", note)
        self.assertIn("한국어 개요", note)
        self.assertIn("#### Summary (KO)", note)
        self.assertIn("한국어 요약", note)
        self.assertIn("#### Detail (KO)", note)
        self.assertIn("한국어 상세", note)

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

    def test_localize_capture_calls_bucky_for_english_capture(self):
        capture = {
            "overviewText": "English overview",
            "cards": [
                {"title": "Card 1", "summary": "English summary", "detailText": "English detail"},
            ],
        }
        localized = {
            "overviewKo": "한국어 개요",
            "cards": [
                {"summaryKo": "한국어 요약", "detailKo": "한국어 상세"},
            ],
        }

        with mock.patch.object(collector, "_run_bucky_localizer", return_value=localized) as localizer:
            result = collector.localize_capture(capture)

        self.assertEqual(result["overviewKo"], "한국어 개요")
        self.assertEqual(result["cards"][0]["summaryKo"], "한국어 요약")
        localizer.assert_called_once()


if __name__ == "__main__":
    unittest.main()
