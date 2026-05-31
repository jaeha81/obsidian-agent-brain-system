import sys
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
