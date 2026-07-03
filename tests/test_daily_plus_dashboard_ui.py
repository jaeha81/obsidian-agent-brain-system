import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DAILY_PLUS_PATH = ROOT / "docs" / "daily-plus.html"


class DailyPlusDashboardUiTests(unittest.TestCase):
    def test_has_quick_navigation_menu(self):
        html = DAILY_PLUS_PATH.read_text(encoding="utf-8")
        self.assertIn("빠른 이동", html)
        self.assertIn("#daily-plus-candidates", html)
        self.assertIn("#daily-plus-results", html)

    def test_removes_duplicate_bucky_message_section(self):
        html = DAILY_PLUS_PATH.read_text(encoding="utf-8")
        self.assertNotIn("<h2>Bucky 메시지</h2>", html)
        self.assertNotIn('id="buckyMessage"', html)

    def test_uses_combined_execute_button_for_cards(self):
        html = DAILY_PLUS_PATH.read_text(encoding="utf-8")
        self.assertIn("승인/구현", html)
        self.assertNotIn('data-action="approve"', html)
        self.assertNotIn('data-action="implement"', html)

    def test_exposes_candidate_progress_status_controls(self):
        html = DAILY_PLUS_PATH.read_text(encoding="utf-8")
        self.assertIn("진행현황", html)
        self.assertIn("가능", html)
        self.assertIn("충돌", html)
        self.assertIn("오류", html)
        self.assertIn("클리어", html)
        self.assertIn("dailyPlusCardStatus", html)

    def test_daily_plus_payload_targets_dedicated_channel(self):
        html = DAILY_PLUS_PATH.read_text(encoding="utf-8")
        self.assertIn('target_channel: "jh-오늘의플러스"', html)
        self.assertIn("target_channel: jh-오늘의플러스", html)

    def test_daily_plus_knowledge_intake_targets_chris(self):
        html = DAILY_PLUS_PATH.read_text(encoding="utf-8")
        self.assertIn("target_channel: jh-chris", html)
        self.assertIn("Chris Knowledge Intake", html)


if __name__ == "__main__":
    unittest.main()
