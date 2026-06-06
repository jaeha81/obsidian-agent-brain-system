"""Tests for wishket_development_request.py

규칙:
- create_local_project_folder / route_to_claude_for_implementation / route_to_codex_for_review
  는 반드시 approval_required 로 분류돼야 한다.
- queue_for_approval 이 생성하는 파일의 frontmatter는 항상
  status: pending_approval / requires_approval: true 여야 한다.
- queued_immediate 상태는 절대 생성되면 안 된다.
"""

import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.wishket_development_request import (  # noqa: E402
    APPROVAL_REQUIRED_ACTIONS,
    IMMEDIATE_ACTIONS,
    normalize_payload,
    queue_for_approval,
    split_actions,
)

# ── 승인 게이트에 고정된 액션 목록 ──────────────────────────────────────────
MUST_BE_APPROVAL = {
    "create_local_project_folder",
    "route_to_claude_for_implementation",
    "route_to_codex_for_review",
}


class TestActionClassification(unittest.TestCase):
    """MUST_BE_APPROVAL 액션은 IMMEDIATE_ACTIONS에 없고 APPROVAL_REQUIRED에 있어야 한다."""

    def test_must_be_approval_not_in_immediate(self):
        leaked = MUST_BE_APPROVAL & IMMEDIATE_ACTIONS
        self.assertEqual(
            leaked,
            set(),
            f"이 액션들이 IMMEDIATE_ACTIONS에 남아 있음: {leaked}",
        )

    def test_must_be_approval_in_approval_required(self):
        missing = MUST_BE_APPROVAL - APPROVAL_REQUIRED_ACTIONS
        self.assertEqual(
            missing,
            set(),
            f"이 액션들이 APPROVAL_REQUIRED_ACTIONS에 없음: {missing}",
        )

    def test_sets_are_disjoint(self):
        overlap = IMMEDIATE_ACTIONS & APPROVAL_REQUIRED_ACTIONS
        self.assertEqual(overlap, set(), f"두 집합이 겹침: {overlap}")


class TestSplitActions(unittest.TestCase):
    """split_actions 함수 동작 검증."""

    def test_folder_and_routing_go_to_approval(self):
        result = split_actions([
            "create_local_project_folder",
            "route_to_claude_for_implementation",
            "route_to_codex_for_review",
        ])
        self.assertEqual(result["immediate"], [])
        self.assertCountEqual(
            result["approval_required"],
            [
                "create_local_project_folder",
                "route_to_claude_for_implementation",
                "route_to_codex_for_review",
            ],
        )

    def test_github_repo_approval(self):
        result = split_actions(["create_github_repository"])
        self.assertIn("create_github_repository", result["approval_required"])
        self.assertNotIn("create_github_repository", result["immediate"])

    def test_analysis_only_actions_stay_immediate(self):
        """읽기/분석 액션은 즉시 실행 가능."""
        result = split_actions(["analyze_requirements", "generate_development_plan"])
        self.assertCountEqual(result["immediate"], ["analyze_requirements", "generate_development_plan"])
        self.assertEqual(result["approval_required"], [])

    def test_unknown_action_defaults_to_approval(self):
        result = split_actions(["totally_unknown_action"])
        self.assertIn("totally_unknown_action", result["approval_required"])
        self.assertNotIn("totally_unknown_action", result["immediate"])

    def test_default_requested_actions_all_require_approval(self):
        """기본 REQUESTED_ACTIONS 집합은 approval_required 없이 통과될 수 없다."""
        from scripts.wishket_development_request import REQUESTED_ACTIONS
        result = split_actions(REQUESTED_ACTIONS)
        self.assertTrue(
            len(result["approval_required"]) > 0,
            "기본 REQUESTED_ACTIONS에 approval_required 액션이 하나도 없음",
        )

    def test_empty_list(self):
        result = split_actions([])
        self.assertEqual(result["immediate"], [])
        self.assertEqual(result["approval_required"], [])


class TestNormalizePayload(unittest.TestCase):
    """normalize_payload가 기본 요청에서 approval_required=True를 반환해야 한다."""

    def _base(self, **kwargs):
        return {
            "project_title": "Test Project",
            "url": "https://www.wishket.com/project/99999/",
            **kwargs,
        }

    def test_default_actions_set_approval_required_true(self):
        payload = normalize_payload(self._base())
        self.assertTrue(
            payload["approval_required"],
            "기본 payload가 approval_required=False를 반환함",
        )

    def test_explicit_local_folder_action_requires_approval(self):
        payload = normalize_payload(self._base(
            requested_actions=["create_local_project_folder"]
        ))
        self.assertTrue(payload["approval_required"])
        self.assertIn("create_local_project_folder", payload["approval_required_actions"])
        self.assertNotIn("create_local_project_folder", payload["immediate_actions"])

    def test_explicit_claude_routing_requires_approval(self):
        payload = normalize_payload(self._base(
            requested_actions=["route_to_claude_for_implementation"]
        ))
        self.assertTrue(payload["approval_required"])

    def test_explicit_codex_routing_requires_approval(self):
        payload = normalize_payload(self._base(
            requested_actions=["route_to_codex_for_review"]
        ))
        self.assertTrue(payload["approval_required"])


class TestQueueForApproval(unittest.TestCase):
    """queue_for_approval 이 생성하는 파일은 항상 pending_approval 이어야 한다."""

    def _make_payload(self, actions=None):
        return normalize_payload({
            "project_title": "Test Project",
            "url": "https://www.wishket.com/project/99999/",
            **({"requested_actions": actions} if actions else {}),
        })

    def _read_frontmatter(self, path: Path) -> dict:
        """YAML-like frontmatter 파싱 (--- 블록)."""
        text = path.read_text(encoding="utf-8")
        lines = text.split("\n")
        fm = {}
        in_fm = False
        for line in lines:
            if line.strip() == "---":
                if not in_fm:
                    in_fm = True
                    continue
                else:
                    break
            if in_fm and ": " in line:
                k, v = line.split(": ", 1)
                try:
                    fm[k.strip()] = json.loads(v.strip())
                except json.JSONDecodeError:
                    fm[k.strip()] = v.strip()
        return fm

    def test_always_pending_approval_default_actions(self):
        payload = self._make_payload()
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch(
                "scripts.wishket_development_request.PENDING_DIR",
                Path(tmpdir),
            ):
                path = queue_for_approval(payload)
            fm = self._read_frontmatter(path)
        self.assertEqual(fm.get("status"), "pending_approval")
        self.assertTrue(fm.get("requires_approval"))

    def test_never_queued_immediate_default(self):
        payload = self._make_payload()
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch(
                "scripts.wishket_development_request.PENDING_DIR",
                Path(tmpdir),
            ):
                path = queue_for_approval(payload)
            content = path.read_text(encoding="utf-8")
        self.assertNotIn("queued_immediate", content)

    def test_always_pending_approval_analysis_only_actions(self):
        """분석 전용 액션만 있어도 pending_approval 이어야 한다."""
        payload = self._make_payload(actions=["analyze_requirements", "generate_development_plan"])
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch(
                "scripts.wishket_development_request.PENDING_DIR",
                Path(tmpdir),
            ):
                path = queue_for_approval(payload)
            fm = self._read_frontmatter(path)
        self.assertEqual(fm.get("status"), "pending_approval")
        self.assertTrue(fm.get("requires_approval"))

    def test_never_queued_immediate_analysis_only(self):
        payload = self._make_payload(actions=["analyze_requirements"])
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch(
                "scripts.wishket_development_request.PENDING_DIR",
                Path(tmpdir),
            ):
                path = queue_for_approval(payload)
            content = path.read_text(encoding="utf-8")
        self.assertNotIn("queued_immediate", content)

    def test_idempotency_same_request_id(self):
        """같은 request_id 로 두 번 호출해도 파일이 하나만 생성된다."""
        payload = self._make_payload()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            with mock.patch(
                "scripts.wishket_development_request.PENDING_DIR",
                tmppath,
            ):
                path1 = queue_for_approval(payload)
                path2 = queue_for_approval(payload)
            files = list(tmppath.glob("*.md"))
        self.assertEqual(path1, path2)
        self.assertEqual(len(files), 1)


class TestGptSessionCollectorNoForceKill(unittest.TestCase):
    """gpt_session_collector.py 에 Chrome 강제 종료 관련 심볼이 없어야 한다."""

    def test_no_kill_chrome_function(self):
        import scripts.gpt_session_collector as col
        self.assertFalse(
            hasattr(col, "_kill_chrome"),
            "_kill_chrome 함수가 아직 남아 있음",
        )

    def test_no_is_chrome_running_function(self):
        import scripts.gpt_session_collector as col
        self.assertFalse(
            hasattr(col, "_is_chrome_running"),
            "_is_chrome_running 함수가 아직 남아 있음",
        )

    def test_collect_mode_no_force_close_param(self):
        import inspect
        import scripts.gpt_session_collector as col
        sig = inspect.signature(col.collect_mode)
        self.assertNotIn(
            "force_close_chrome",
            sig.parameters,
            "collect_mode 에 force_close_chrome 파라미터가 아직 남아 있음",
        )

    def test_dedicated_profile_not_real_chrome(self):
        import scripts.gpt_session_collector as col
        profile = str(col.PROFILE_DIR)
        self.assertNotIn(
            "Google\\Chrome\\User Data",
            profile,
            f"전용 프로파일 경로가 실제 Chrome 프로파일을 가리킴: {profile}",
        )


if __name__ == "__main__":
    unittest.main()
