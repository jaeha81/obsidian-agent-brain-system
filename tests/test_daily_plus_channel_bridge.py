import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _get_discord_bot():
    from scripts import discord_bot  # noqa: PLC0415
    return discord_bot


class DailyPlusChannelBridgeTests(unittest.TestCase):
    def test_pending_daily_plus_briefings_filters_sent_and_nonmatching_files(self):
        discord_bot = _get_discord_bot()
        outbox = ROOT / "ObsidianVault" / "10_AgentBus" / "outbox" / "Bucky"
        sent = {"20260614_090000_daily_plus_dashboard_bucky.md"}

        files = [
            outbox / "20260615_090000_daily_plus_dashboard_bucky.md",
            outbox / "20260614_090000_daily_plus_dashboard_bucky.md",
            outbox / "20260615_other_report.md",
        ]

        pending = discord_bot._pending_daily_plus_briefings(files, sent)

        self.assertEqual(
            pending,
            [outbox / "20260615_090000_daily_plus_dashboard_bucky.md"],
        )

    def test_build_daily_plus_briefing_message_strips_frontmatter(self):
        discord_bot = _get_discord_bot()
        briefing = """---
type: bucky-user-report
scope: daily-plus-dashboard
date: 2026-06-15
status: needs-attention
public_url: https://example.com/daily-plus.html
---

# Bucky Daily Plus 09:00 Report - 2026-06-15

- Dashboard: https://example.com/daily-plus.html
- Status: needs-attention
"""

        message = discord_bot._build_daily_plus_briefing_message(
            "20260615_090000_daily_plus_dashboard_bucky.md",
            briefing,
        )

        self.assertIn("Daily Plus 09:00 Report", message)
        self.assertIn("2026-06-15", message)
        self.assertIn("needs-attention", message)
        self.assertNotIn("type: bucky-user-report", message)


if __name__ == "__main__":
    unittest.main()
