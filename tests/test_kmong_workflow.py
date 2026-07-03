import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import kmong_workflow


class KmongWorkflowTests(unittest.TestCase):
    def test_normalize_login_payload_requires_credential_source_without_secret_values(self):
        payload = kmong_workflow.normalize_payload(
            {
                "action": "login",
                "title": "Kmong login",
                "username": "user@example.com",
                "password": "plain-secret",
                "requested_actions": ["login_kmong"],
            }
        )

        self.assertEqual(payload["type"], "kmong_workflow_request")
        self.assertEqual(payload["dashboard_type"], "kmong")
        self.assertEqual(payload["credential_source"], "environment")
        self.assertTrue(payload["approval_required"])
        self.assertIn("login_kmong", payload["approval_required_actions"])
        rendered = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("plain-secret", rendered)
        self.assertNotIn("user@example.com", rendered)

    def test_sync_and_analysis_actions_are_immediate_but_customer_send_is_approval_gated(self):
        payload = kmong_workflow.normalize_payload(
            {
                "action": "sync_requests",
                "title": "Sync Kmong requests",
                "requested_actions": [
                    "sync_kmong_requests",
                    "analyze_request",
                    "draft_customer_reply",
                    "send_customer_reply",
                    "accept_order",
                ],
            }
        )

        self.assertEqual(
            payload["immediate_actions"],
            ["sync_kmong_requests", "analyze_request", "draft_customer_reply"],
        )
        self.assertEqual(payload["approval_required_actions"], ["send_customer_reply", "accept_order"])
        self.assertEqual(payload["execution_mode"], "approval_required")

    def test_challenge_status_stops_automation_for_manual_authentication(self):
        status = kmong_workflow.login_status_from_event(
            {"status": "challenge", "challenge_type": "otp", "message": "OTP required"}
        )

        self.assertFalse(status["can_continue"])
        self.assertEqual(status["state"], "manual_auth_required")
        self.assertIn("otp", status["reason"])

    def test_enqueue_request_writes_redacted_agentbus_note(self):
        payload = kmong_workflow.normalize_payload(
            {
                "request_id": "kmong-test-1",
                "action": "draft_customer_reply",
                "title": "Build a landing page",
                "summary": "Customer wants a sales page.",
                "requested_actions": ["draft_customer_reply"],
                "username": "user@example.com",
                "password": "plain-secret",
            }
        )
        with tempfile.TemporaryDirectory(dir=r"C:\tmp") as tmpdir:
            inbox = Path(tmpdir) / "kmong_inbox"
            with mock.patch("scripts.kmong_workflow.KMONG_INBOX_DIR", inbox):
                path = kmong_workflow.enqueue_request(payload)

            text = path.read_text(encoding="utf-8")
            self.assertIn("kmong_request_id: kmong-test-1", text)
            self.assertIn("Build a landing page", text)
            self.assertNotIn("plain-secret", text)
            self.assertNotIn("user@example.com", text)


if __name__ == "__main__":
    unittest.main()
