import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts import daily_plus_morning_report as morning


class DailyPlusMorningReportTests(unittest.TestCase):
    def test_report_needs_attention_for_zero_candidate_404_capture(self):
        report_text = """---
date: 2026-05-31
card_count: 0
candidate_count: 0
---

# Pulse Evolution Report - 2026-05-31
"""
        capture_text = """---
date: 2026-05-31
card_count: 0
---

# ChatGPT Pulse - 2026-05-31

## Overview

404 Not Found
"""

        self.assertTrue(morning.report_needs_attention(report_text, capture_text))

    def test_report_needs_attention_false_for_candidate_report(self):
        report_text = """---
date: 2026-05-30
card_count: 3
candidate_count: 3
---

### P1 · Card 1: Example
"""
        capture_text = "## Overview\n\nPulse\n\n## Pulse Cards"

        self.assertFalse(morning.report_needs_attention(report_text, capture_text))

    def test_generate_dashboard_falls_back_to_subprocess_on_permission_error(self):
        output_path = ROOT / "docs" / "daily-plus.html"
        completed = mock.Mock(
            returncode=0,
            stdout=f"[daily-plus-dashboard] wrote {output_path}\n",
            stderr="",
        )

        with mock.patch.object(morning, "generate", side_effect=PermissionError("denied")):
            with mock.patch.object(morning.subprocess, "run", return_value=completed) as run_mock:
                output = morning.generate_dashboard("2026-06-04")

        self.assertEqual(output, output_path)
        run_mock.assert_called_once()

    def test_generate_dashboard_raises_when_subprocess_fallback_fails(self):
        completed = mock.Mock(returncode=1, stdout="", stderr="fallback failed")

        with mock.patch.object(morning, "generate", side_effect=PermissionError("denied")):
            with mock.patch.object(morning.subprocess, "run", return_value=completed):
                with self.assertRaises(RuntimeError):
                    morning.generate_dashboard("2026-06-04")

    def test_generate_dashboard_retries_without_date_when_dated_fallback_fails(self):
        output_path = ROOT / "docs" / "daily-plus.html"
        first = mock.Mock(returncode=1, stdout="", stderr="dated failed")
        second = mock.Mock(
            returncode=0,
            stdout=f"[daily-plus-dashboard] wrote {output_path}\n",
            stderr="",
        )

        with mock.patch.object(morning, "generate", side_effect=PermissionError("denied")):
            with mock.patch.object(morning.subprocess, "run", side_effect=[first, second]) as run_mock:
                output = morning.generate_dashboard("2026-06-04")

        self.assertEqual(output, output_path)
        self.assertEqual(run_mock.call_count, 2)

    def test_dashboard_is_current_requires_date_and_report_marker(self):
        path = mock.Mock(spec=Path)
        path.exists.return_value = True
        path.read_text.return_value = (
            "2026-06-04\nObsidianVault\\00_UPGRADE\\pulse-evolution\\2026-06-04.md\n"
        )

        self.assertTrue(morning.dashboard_is_current(path, "2026-06-04"))
        self.assertFalse(morning.dashboard_is_current(path, "2026-06-05"))

    def test_write_text_or_keep_existing_accepts_matching_existing_file(self):
        path = mock.Mock(spec=Path)
        path.write_text.side_effect = PermissionError("denied")
        path.exists.return_value = True
        path.read_text.return_value = "date: 2026-06-04\nstatus: ready\nhttps://jaeha81.github.io/obsidian-agent-brain-system/daily-plus.html\n"

        morning.write_text_or_keep_existing(
            path,
            "body",
            ["date: 2026-06-04", "status: ready", morning.PUBLIC_URL],
        )


if __name__ == "__main__":
    unittest.main()
