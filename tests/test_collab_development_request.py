import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TEST_TMP_ROOT = Path(r"C:\tmp")
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts import collab_development_request as router  # noqa: E402
from scripts import collab_proposal_workflow as workflow  # noqa: E402


class TestCollabDevelopmentRequest(unittest.TestCase):
    def setUp(self):
        self.base_payload = {
            "request_id": "collab-1234",
            "summary": "AI dashboard build",
            "email": "hello@example.com",
            "company": "Example Studio",
            "body": "Need proposal and implementation.",
        }

    def test_normalize_payload_builds_request_slug_and_actions(self):
        payload = router.normalize_payload(self.base_payload)
        self.assertEqual(payload["type"], "collab_development_request")
        self.assertIn("route_to_claude_for_implementation", payload["requested_actions"])
        self.assertTrue(payload["request_slug"])

    def test_dispatch_rejects_unapproved_workflow(self):
        payload = router.normalize_payload(self.base_payload)
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            workflow_root = Path(tmpdir) / "workflow"
            with mock.patch.object(workflow, "WORKFLOW_ROOT", workflow_root), mock.patch.object(
                router.workflow, "WORKFLOW_ROOT", workflow_root
            ), mock.patch.object(router, "INBOX_DIR", Path(tmpdir) / "inbox"):
                workflow.ensure_workspace(payload)
                with self.assertRaisesRegex(PermissionError, "approved"):
                    router.dispatch_request(payload, require_workflow_approval=True)

    def test_dispatch_creates_claude_and_codex_inbox_files_after_approval(self):
        payload = router.normalize_payload(self.base_payload)
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            workflow_root = Path(tmpdir) / "workflow"
            with mock.patch.object(workflow, "WORKFLOW_ROOT", workflow_root), mock.patch.object(
                router.workflow, "WORKFLOW_ROOT", workflow_root
            ), mock.patch.object(router, "INBOX_DIR", Path(tmpdir) / "inbox"):
                workflow.ensure_workspace(payload)
                workflow.record_approval(payload, "admin")
                mode, claude_path, codex_path = router.dispatch_request(payload, require_workflow_approval=True)
                self.assertEqual(mode, "immediate")
                self.assertTrue(claude_path.exists())
                self.assertTrue(codex_path.exists())


if __name__ == "__main__":
    unittest.main()
