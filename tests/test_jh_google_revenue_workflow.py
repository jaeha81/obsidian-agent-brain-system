import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import jh_google_revenue_workflow as workflow


class JhGoogleRevenueWorkflowTests(unittest.TestCase):
    def test_content_generation_requires_human_review(self):
        payload = workflow.normalize_payload(
            {
                "action": "draft_article",
                "title": "블로그 애드센스 승인 체크리스트",
                "requested_actions": ["score_keyword", "draft_outline", "draft_article"],
            }
        )

        self.assertEqual(payload["type"], "jh_google_revenue_request")
        self.assertEqual(payload["dashboard_type"], "jh_google_revenue")
        self.assertEqual(payload["execution_mode"], "immediate")
        self.assertTrue(payload["human_review_required"])
        self.assertIn("draft_article", payload["immediate_actions"])

    def test_forbidden_adsense_actions_are_blocked(self):
        payload = workflow.normalize_payload(
            {
                "action": "click_ads",
                "title": "Forbidden traffic shortcut",
                "requested_actions": ["click_ads", "simulate_traffic", "draft_article"],
            }
        )

        self.assertEqual(payload["execution_mode"], "blocked")
        self.assertTrue(payload["approval_required"])
        self.assertEqual(payload["forbidden_actions"], ["click_ads", "simulate_traffic"])
        self.assertIn("draft_article", payload["immediate_actions"])

    def test_external_send_actions_require_approval(self):
        payload = workflow.normalize_payload(
            {
                "action": "send_make_webhook",
                "title": "Send reviewed draft to Make",
                "requested_actions": ["prepare_make_webhook_payload", "send_make_webhook"],
            }
        )

        self.assertEqual(payload["execution_mode"], "approval_required")
        self.assertEqual(payload["immediate_actions"], ["prepare_make_webhook_payload"])
        self.assertEqual(payload["approval_required_actions"], ["send_make_webhook"])

    def test_enqueue_request_writes_redacted_note(self):
        payload = workflow.normalize_payload(
            {
                "request_id": "jhgrev-test-1",
                "action": "draft_article",
                "title": "Make.com 블로그 운영 기록 자동 저장",
                "requested_actions": ["draft_article"],
                "webhook_url": "https://hooks.example.test/secret",
                "access_token": "plain-token",
            }
        )

        with tempfile.TemporaryDirectory(dir=r"C:\tmp") as tmpdir:
            inbox = Path(tmpdir) / "jh_google_revenue_inbox"
            with mock.patch("scripts.jh_google_revenue_workflow.INBOX_DIR", inbox):
                path = workflow.enqueue_request(payload)

            text = path.read_text(encoding="utf-8")
            self.assertIn("request_id: jhgrev-test-1", text)
            self.assertIn("Make.com 블로그 운영 기록 자동 저장", text)
            self.assertIn("Human review required: True", text)
            self.assertNotIn("plain-token", text)
            self.assertNotIn("hooks.example.test/secret", text)
            parsed = json.loads(text.split("```json\n", 1)[1].split("\n```", 1)[0])
            self.assertEqual(parsed["redacted_input"]["access_token"], "[redacted]")


if __name__ == "__main__":
    unittest.main()
