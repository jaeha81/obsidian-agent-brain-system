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

from scripts.wishket_development_request import normalize_payload  # noqa: E402
from scripts import wishket_proposal_workflow as workflow  # noqa: E402


class WishketProposalWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.payload = normalize_payload(
            {
                "project_title": "Python LangChain AI backend",
                "url": "https://www.wishket.com/project/155733/",
                "summary": "Build the backend and proposal workflow.",
                "budget": "780만원",
            }
        )

    def test_ensure_project_workspace_bootstraps_status_file(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            root = Path(tmpdir)
            with mock.patch.object(workflow, "WORKFLOW_ROOT", root):
                workspace = workflow.ensure_project_workspace(self.payload)
                self.assertEqual(workspace, root / self.payload["project_slug"])
                status = json.loads((workspace / "status.json").read_text(encoding="utf-8"))
        self.assertEqual(status["workflow_state"], "idle")
        self.assertFalse(status["approved"])
        self.assertEqual(status["project_id"], "project-155733")

    def test_mark_proposal_ready_updates_version_and_file(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            root = Path(tmpdir)
            with mock.patch.object(workflow, "WORKFLOW_ROOT", root):
                workflow.ensure_project_workspace(self.payload)
                status = workflow.mark_proposal_ready(self.payload, "proposal-v1.md")
        self.assertEqual(status["workflow_state"], "proposal_ready")
        self.assertEqual(status["proposal_version"], 1)
        self.assertEqual(status["current_proposal_file"], "proposal-v1.md")

    def test_record_feedback_marks_revision_pending(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            root = Path(tmpdir)
            with mock.patch.object(workflow, "WORKFLOW_ROOT", root):
                workflow.ensure_project_workspace(self.payload)
                status = workflow.record_feedback(self.payload, "문구를 더 간결하게 정리")
                feedback_text = (root / self.payload["project_slug"] / "feedback.md").read_text(encoding="utf-8")
        self.assertEqual(status["workflow_state"], "feedback_in_progress")
        self.assertTrue(status["feedback_pending"])
        self.assertEqual(status["feedback_count"], 1)
        self.assertIn("문구를 더 간결하게 정리", feedback_text)

    def test_record_approval_accepts_dashboard_or_discord(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            root = Path(tmpdir)
            with mock.patch.object(workflow, "WORKFLOW_ROOT", root):
                workflow.ensure_project_workspace(self.payload)
                status = workflow.record_approval(self.payload, "dashboard")
                reloaded = workflow.load_status(self.payload["project_slug"])
        self.assertTrue(status["approved"])
        self.assertEqual(status["approved_via"], "dashboard")
        self.assertEqual(reloaded["workflow_state"], "approved")


if __name__ == "__main__":
    unittest.main()
