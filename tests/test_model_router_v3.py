"""scripts/model_router.py V3 Stage 7 테스트 — provider 후보열 + 기존 동작 회귀 + stdout 보존.

provider_candidates: routing_policy.yaml 정본, 형식 불량·로드 실패 시 안전 기본값.
기존 select_model/fallback_chain 동작 무변경 확인 (bucky_client 소비 경로).
"""

import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from core.config import load_model_registry, load_routing_policy  # noqa: E402
from model_router import (  # noqa: E402
    DEFAULT_PROVIDER_CHAIN,
    TASK_TO_MODEL,
    fallback_chain,
    provider_candidates,
    select_model,
)


class ProviderCandidatesYamlTests(unittest.TestCase):
    """리포에 실존하는 config/routing_policy.yaml 기반."""

    def setUp(self):
        if not load_routing_policy():
            self.skipTest("routing_policy.yaml 로드 불가")

    def test_review_override(self):
        self.assertEqual(provider_candidates("review"), ["codex_pro", "claude_code"])

    def test_default_chain_for_code(self):
        self.assertEqual(provider_candidates("code"), ["claude_code", "gemini"])

    def test_unknown_task_uses_defaults(self):
        self.assertEqual(provider_candidates("no_such_task"), provider_candidates("code"))

    def test_task_type_normalized(self):
        self.assertEqual(provider_candidates("  REVIEW  "), provider_candidates("review"))

    def test_candidates_are_registry_keys(self):
        providers = set(load_model_registry().get("providers", {}))
        if not providers:
            self.skipTest("model_registry.yaml 로드 불가")
        for task in list(TASK_TO_MODEL) + ["review", "no_such_task"]:
            for p in provider_candidates(task):
                self.assertIn(p, providers, f"task={task} provider={p}")


class ProviderCandidatesInjectedPolicyTests(unittest.TestCase):
    """정책 주입 — yaml 없이 순수 로직 검증."""

    POLICY = {
        "defaults": {"provider_chain": ["claude_code", "gemini"]},
        "overrides": {"review": ["codex_pro", "claude_code"]},
    }

    def test_override_wins(self):
        self.assertEqual(provider_candidates("review", self.POLICY), ["codex_pro", "claude_code"])

    def test_fallthrough_to_defaults(self):
        self.assertEqual(provider_candidates("chat", self.POLICY), ["claude_code", "gemini"])

    def test_empty_policy_uses_builtin(self):
        self.assertEqual(provider_candidates("code", {}), DEFAULT_PROVIDER_CHAIN)

    def test_non_dict_policy_uses_builtin(self):
        self.assertEqual(provider_candidates("code", "garbage"), DEFAULT_PROVIDER_CHAIN)

    def test_non_list_override_ignored(self):
        policy = {"overrides": {"review": "codex_pro"}, "defaults": {"provider_chain": ["claude_code"]}}
        self.assertEqual(provider_candidates("review", policy), ["claude_code"])

    def test_empty_or_bad_chain_ignored(self):
        for bad in ([], [""], [None], [1, 2]):
            policy = {"defaults": {"provider_chain": bad}}
            self.assertEqual(provider_candidates("code", policy), DEFAULT_PROVIDER_CHAIN, repr(bad))

    def test_returns_copy_not_reference(self):
        out = provider_candidates("review", self.POLICY)
        out.append("mutated")
        self.assertEqual(provider_candidates("review", self.POLICY), ["codex_pro", "claude_code"])


class ExistingBehaviorRegressionTests(unittest.TestCase):
    """기존 TASK_TO_MODEL/폴백 동작 무변경 (bucky_client가 소비하는 공개 API)."""

    def test_tier_routing_unchanged(self):
        self.assertEqual(select_model("classify"), "haiku")
        self.assertEqual(select_model("code"), "sonnet")
        self.assertEqual(select_model("review"), "opus")

    def test_unknown_task_defaults_to_sonnet(self):
        self.assertEqual(select_model("no_such_task"), "sonnet")

    def test_override_and_env_force(self):
        self.assertEqual(select_model("classify", override="opus"), "opus")
        with mock.patch.dict(os.environ, {"BUCKY_FORCE_MODEL": "haiku"}):
            self.assertEqual(select_model("review"), "haiku")

    def test_fallback_chains_unchanged(self):
        self.assertEqual(fallback_chain("sonnet"), ["sonnet", "haiku", "opus"])
        self.assertEqual(fallback_chain("haiku"), ["haiku", "sonnet"])
        self.assertEqual(fallback_chain("opus"), ["opus", "sonnet", "haiku"])


class StdoutPreservationTests(unittest.TestCase):
    """import 시점 stdout 재래핑이 호출자의 미flush 버퍼를 유실시키지 않는다 (Stage 7 수정).

    파이프 + 비utf8 인코딩 강제 → 재래핑 경로를 실제로 태운다.
    수정 전 코드에서는 'before-import'가 유실되어 FAIL하던 시나리오.
    """

    def test_print_before_import_survives_rewrap(self):
        code = (
            f"import sys; sys.path.insert(0, {str(SCRIPTS)!r}); "
            "print('before-import'); import model_router; print('after-import')"
        )
        env = os.environ.copy()
        env.pop("PYTHONUTF8", None)
        env["PYTHONIOENCODING"] = "cp949"  # 비utf8 스트림 → win32 재래핑 발동
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60, env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("before-import", result.stdout)
        self.assertIn("after-import", result.stdout)

    def test_custom_wrapper_survives_import_not_closed(self):
        """비utf8 custom TextIOWrapper가 있어도 import 후 stdout이 닫히지 않는다.

        wrapper 교체 방식에서는 기존 wrapper GC가 공유 buffer를 닫아
        sys.stdout.closed=True가 되던 시나리오 — reconfigure 전환으로 고정.
        """
        code = (
            "import sys, io; "
            f"sys.path.insert(0, {str(SCRIPTS)!r}); "
            "sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='cp949', errors='replace'); "
            "import gc; import model_router; gc.collect(); "
            "assert not sys.stdout.closed, 'stdout closed after import'; "
            "print('still-open', flush=True)"
        )
        env = os.environ.copy()
        env.pop("PYTHONUTF8", None)
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60, env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("still-open", result.stdout)


if __name__ == "__main__":
    unittest.main()
