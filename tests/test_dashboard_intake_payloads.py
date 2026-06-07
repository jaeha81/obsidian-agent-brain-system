import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class RepoDashboardIntakePayloadTests(unittest.TestCase):
    def test_repo_single_item_payload_has_required_plan_fields(self):
        html = read_text("docs/index.html")
        self.assertIn("dashboard_type: 'repo'", html)
        self.assertIn("target_channel: 'jh-레포대시보드'", html)
        self.assertIn("item_id: repo.id", html)
        self.assertIn("source_dashboard_url: location.href", html)

    def test_repo_batch_payload_has_required_plan_fields(self):
        html = read_text("docs/index.html")
        self.assertIn("dashboard_type: 'repo'", html)
        self.assertIn("target_channel: 'jh-레포대시보드'", html)
        self.assertIn("item_id: checked.map(r => r.id).join(',')", html)
        self.assertIn("source_dashboard_url: location.href", html)


class WishketDashboardIntakePayloadTests(unittest.TestCase):
    def test_wishket_payload_has_stable_request_id(self):
        html = read_text("docs/wishket.html")
        self.assertIn("request_id:", html)
        self.assertIn("wishket-", html)


class DashboardProgressUiTests(unittest.TestCase):
    def test_repo_dashboard_has_progress_status_ui(self):
        html = read_text("docs/index.html")
        self.assertIn("진행상황", html)
        self.assertIn("다음 플랜", html)
        self.assertIn("이어서 작업", html)
        self.assertIn("세션", html)

    def test_wishket_dashboard_has_progress_status_ui(self):
        html = read_text("docs/wishket.html")
        self.assertIn("진행상황", html)
        self.assertIn("다음 플랜", html)
        self.assertIn("이어서 작업", html)
        self.assertIn("세션", html)


class TaskChecklistRoleTests(unittest.TestCase):
    def test_task_board_defines_role_separation(self):
        html = read_text("docs/task-board.html")
        self.assertIn("태스크보드는 실행 작업 관리", html)
        self.assertIn("체크리스트는 확인/승인/재개 목록", html)

    def test_checklist_defines_role_separation(self):
        html = read_text("docs/checklist.html")
        self.assertIn("태스크보드는 실행 작업 관리", html)
        self.assertIn("체크리스트는 확인/승인/재개 목록", html)


if __name__ == "__main__":
    unittest.main()
