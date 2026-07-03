import json
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

from scripts import collab_proposal_workflow as workflow  # noqa: E402


class TestCollabProposalWorkflow(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "request_id": "collab-4f3b9c8a",
            "request_slug": "collab-4f3b9c8a-ai-agent-dashboard-build",
            "project_title": "AI agent dashboard build",
            "summary": "Need proposal and development support.",
        }

    def test_ensure_workspace_bootstraps_status_json(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            with mock.patch.object(workflow, "WORKFLOW_ROOT", Path(tmpdir)):
                workspace = workflow.ensure_workspace(self.payload)
                status = json.loads((workspace / "status.json").read_text(encoding="utf-8"))
        self.assertEqual(status["workflow_state"], "new")
        self.assertFalse(status["approved"])

    def test_mark_proposal_started_updates_state(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            with mock.patch.object(workflow, "WORKFLOW_ROOT", Path(tmpdir)):
                workflow.ensure_workspace(self.payload)
                status = workflow.mark_proposal_started(self.payload, "admin")
        self.assertEqual(status["workflow_state"], "proposal_in_progress")
        self.assertTrue(status["discord_dispatched"])

    def test_record_approval_unlocks_development(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            with mock.patch.object(workflow, "WORKFLOW_ROOT", Path(tmpdir)):
                workflow.ensure_workspace(self.payload)
                status = workflow.record_approval(self.payload, "admin")
        self.assertEqual(status["workflow_state"], "approved")
        self.assertTrue(status["approved"])


if __name__ == "__main__":
    unittest.main()
