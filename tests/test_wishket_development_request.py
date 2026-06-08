"""Tests for wishket_development_request.py."""

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

from scripts.wishket_development_request import (  # noqa: E402
    APPROVAL_REQUIRED_ACTIONS,
    IMMEDIATE_ACTIONS,
    dispatch_request,
    enqueue_codex_review_request,
    enqueue_immediate_request,
    normalize_payload,
    queue_for_approval,
    split_actions,
)


class TestActionClassification(unittest.TestCase):
    def test_route_actions_are_immediate(self):
        self.assertIn("route_to_claude_for_implementation", IMMEDIATE_ACTIONS)
        self.assertIn("route_to_codex_for_review", IMMEDIATE_ACTIONS)
        self.assertNotIn("route_to_claude_for_implementation", APPROVAL_REQUIRED_ACTIONS)
        self.assertNotIn("route_to_codex_for_review", APPROVAL_REQUIRED_ACTIONS)

    def test_folder_and_repo_creation_remain_approval_required(self):
        self.assertIn("create_local_project_folder", APPROVAL_REQUIRED_ACTIONS)
        self.assertIn("create_github_repository", APPROVAL_REQUIRED_ACTIONS)


class TestSplitActions(unittest.TestCase):
    def test_agent_routing_actions_go_immediate(self):
        result = split_actions(
            [
                "generate_development_plan",
                "route_to_claude_for_implementation",
                "route_to_codex_for_review",
            ]
        )
        self.assertCountEqual(
            result["immediate"],
            [
                "generate_development_plan",
                "route_to_claude_for_implementation",
                "route_to_codex_for_review",
            ],
        )
        self.assertEqual(result["approval_required"], [])

    def test_external_side_effects_stay_approval_required(self):
        result = split_actions(["create_local_project_folder", "create_github_repository"])
        self.assertEqual(result["immediate"], [])
        self.assertCountEqual(
            result["approval_required"],
            ["create_local_project_folder", "create_github_repository"],
        )


class TestNormalizePayload(unittest.TestCase):
    def _base(self, **kwargs):
        return {
            "project_title": "Test Project",
            "url": "https://www.wishket.com/project/99999/",
            **kwargs,
        }

    def test_dashboard_style_payload_is_immediate(self):
        payload = normalize_payload(
            self._base(
                requested_actions=[
                    "generate_development_plan",
                    "route_to_claude_for_implementation",
                    "route_to_codex_for_review",
                ]
            )
        )
        self.assertFalse(payload["approval_required"])
        self.assertEqual(payload["execution_mode"], "immediate")
        self.assertIn("route_to_claude_for_implementation", payload["immediate_actions"])

    def test_project_creation_payload_requires_approval(self):
        payload = normalize_payload(
            self._base(requested_actions=["create_local_project_folder"])
        )
        self.assertTrue(payload["approval_required"])
        self.assertEqual(payload["execution_mode"], "approval_required")
        self.assertIn("create_local_project_folder", payload["approval_required_actions"])


class TestRoutingOutputs(unittest.TestCase):
    def _read_frontmatter(self, path: Path) -> dict:
        text = path.read_text(encoding="utf-8")
        lines = text.split("\n")
        fm = {}
        in_fm = False
        for line in lines:
            if line.strip() == "---":
                if not in_fm:
                    in_fm = True
                    continue
                break
            if in_fm and ": " in line:
                k, v = line.split(": ", 1)
                try:
                    fm[k.strip()] = json.loads(v.strip())
                except json.JSONDecodeError:
                    fm[k.strip()] = v.strip()
        return fm

    def test_queue_for_approval_writes_pending_file(self):
        payload = normalize_payload(
            {
                "project_title": "Approval Project",
                "url": "https://www.wishket.com/project/11111/",
                "requested_actions": ["create_local_project_folder"],
            }
        )
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            with mock.patch("scripts.wishket_development_request.PENDING_DIR", Path(tmpdir)), mock.patch(
                "scripts.wishket_development_request.DEV_ROOT", Path(tmpdir) / "dev"
            ):
                path = queue_for_approval(payload)
            fm = self._read_frontmatter(path)
        self.assertEqual(fm["status"], "pending_approval")
        self.assertTrue(fm["requires_approval"])

    def test_enqueue_immediate_request_writes_inbox_file(self):
        payload = normalize_payload(
            {
                "project_title": "Immediate Project",
                "url": "https://www.wishket.com/project/22222/",
                "requested_actions": [
                    "generate_development_plan",
                    "route_to_claude_for_implementation",
                    "route_to_codex_for_review",
                ],
            }
        )
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            with mock.patch("scripts.wishket_development_request.INBOX_DIR", Path(tmpdir)), mock.patch(
                "scripts.wishket_development_request.DEV_ROOT", Path(tmpdir) / "dev"
            ):
                path = enqueue_immediate_request(payload)
            fm = self._read_frontmatter(path)
            content = path.read_text(encoding="utf-8")
        self.assertEqual(fm["type"], "implementation_request")
        self.assertEqual(fm["status"], "pending")
        self.assertFalse(fm["requires_approval"])
        self.assertIn("wishket_request_id", fm)
        self.assertIn("Wishket Immediate Execution Request", content)

    def test_enqueue_codex_review_request_writes_inbox_file(self):
        payload = normalize_payload(
            {
                "project_title": "Codex Review Project",
                "url": "https://www.wishket.com/project/55555/",
                "requested_actions": ["route_to_codex_for_review"],
            }
        )
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            with mock.patch("scripts.wishket_development_request.INBOX_DIR", Path(tmpdir)), mock.patch(
                "scripts.wishket_development_request.DEV_ROOT", Path(tmpdir) / "dev"
            ):
                path = enqueue_codex_review_request(payload)
            fm = self._read_frontmatter(path)
            content = path.read_text(encoding="utf-8")
        self.assertEqual(fm["type"], "review_request")
        self.assertEqual(fm["router"], "Codex")
        self.assertFalse(fm["requires_approval"])
        self.assertIn("wishket_review_id", fm)
        self.assertIn("Codex Review Request", content)

    def test_dispatch_request_selects_expected_route(self):
        immediate_payload = normalize_payload(
            {
                "project_title": "Immediate Dispatch",
                "url": "https://www.wishket.com/project/33333/",
                "requested_actions": ["route_to_claude_for_implementation"],
            }
        )
        approval_payload = normalize_payload(
            {
                "project_title": "Approval Dispatch",
                "url": "https://www.wishket.com/project/44444/",
                "requested_actions": ["create_github_repository"],
            }
        )
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            inbox = Path(tmpdir) / "inbox"
            pending = Path(tmpdir) / "pending"
            with mock.patch("scripts.wishket_development_request.INBOX_DIR", inbox), mock.patch(
                "scripts.wishket_development_request.PENDING_DIR", pending
            ), mock.patch(
                "scripts.wishket_development_request.DEV_ROOT", Path(tmpdir) / "dev"
            ):
                mode1, path1, codex_path1 = dispatch_request(immediate_payload)
                mode2, path2, codex_path2 = dispatch_request(approval_payload)
            self.assertTrue(path1.exists())
            self.assertTrue(path2.exists())
            self.assertIsNotNone(codex_path1)
            self.assertTrue(codex_path1.exists())
            self.assertIsNone(codex_path2)
        self.assertEqual(mode1, "immediate")
        self.assertEqual(mode2, "pending_approval")

    def test_immediate_dispatch_creates_both_claude_and_codex_files(self):
        payload = normalize_payload(
            {
                "project_title": "Dual Dispatch Project",
                "url": "https://www.wishket.com/project/66666/",
                "requested_actions": [
                    "generate_development_plan",
                    "route_to_claude_for_implementation",
                    "route_to_codex_for_review",
                ],
            }
        )
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            inbox = Path(tmpdir) / "inbox"
            with mock.patch("scripts.wishket_development_request.INBOX_DIR", inbox), mock.patch(
                "scripts.wishket_development_request.DEV_ROOT", Path(tmpdir) / "dev"
            ):
                mode, claude_path, codex_path = dispatch_request(payload)
            claude_fm = self._read_frontmatter(claude_path)
            codex_fm = self._read_frontmatter(codex_path)
        self.assertEqual(mode, "immediate")
        self.assertEqual(claude_fm["router"], "ClaudeCode")
        self.assertEqual(claude_fm["type"], "implementation_request")
        self.assertEqual(codex_fm["router"], "Codex")
        self.assertEqual(codex_fm["type"], "review_request")


if __name__ == "__main__":
    unittest.main()
