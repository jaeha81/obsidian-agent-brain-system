"""scripts/core/provider_adapter.py + scripts/providers/ 단위 테스트 — V3 Stage 6.

계약 검증: 키 없음→disabled, CLI 없음→failed, run() 예외 무전파, 팩토리-레지스트리 정합.
실제 CLI/API 호출 없음 — 전부 가짜 entry 또는 mock.
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from core.agent_result import AgentResult  # noqa: E402
from core.provider_adapter import (  # noqa: E402
    HEALTH_DISABLED,
    HEALTH_FAILED,
    HEALTH_OK,
    Health,
    ProviderAdapter,
)
from core.config import load_model_registry  # noqa: E402
from core.task_spec import TaskSpec, new_task_id  # noqa: E402
from providers import ADAPTERS, all_adapters, get_adapter  # noqa: E402
from providers.claude_cli_adapter import ClaudeCliAdapter  # noqa: E402
from providers.codex_cli_adapter import CodexCliAdapter  # noqa: E402
from providers.gemini_adapter import GeminiAdapter  # noqa: E402

VALID_SPEC = TaskSpec(task_id=new_task_id(), task_type="code")
MISSING_EXE = r"C:\bucky_test_nonexistent\claude.exe"


def _entry(**kwargs) -> dict:
    base = {"enabled": True, "env_keys": []}
    base.update(kwargs)
    return base


class FactoryTests(unittest.TestCase):
    def test_get_adapter_returns_matching_class(self):
        for name, cls in ADAPTERS.items():
            adapter = get_adapter(name)
            self.assertIsInstance(adapter, cls, name)
            self.assertEqual(adapter.name, name)

    def test_get_adapter_unknown_name_returns_none(self):
        self.assertIsNone(get_adapter("no_such_provider"))

    def test_all_adapters_covers_registry(self):
        self.assertEqual(set(all_adapters()), set(ADAPTERS))

    def test_adapter_names_match_model_registry(self):
        providers = load_model_registry().get("providers", {})
        if not providers:
            self.skipTest("model_registry.yaml 로드 불가")
        self.assertEqual(set(ADAPTERS), set(providers))


class HealthcheckTests(unittest.TestCase):
    def test_registry_disabled_returns_disabled(self):
        adapter = ProviderAdapter(_entry(enabled=False))
        h = adapter.healthcheck()
        self.assertEqual(h.status, HEALTH_DISABLED)
        self.assertFalse(h.ok)

    def test_openai_from_registry_is_disabled(self):
        h = get_adapter("openai_gpt").healthcheck()
        self.assertEqual(h.status, HEALTH_DISABLED)

    def test_missing_env_key_returns_disabled(self):
        adapter = ProviderAdapter(_entry(env_keys=["BUCKY_TEST_NONEXISTENT_KEY"]))
        h = adapter.healthcheck()
        self.assertEqual(h.status, HEALTH_DISABLED)
        self.assertIn("BUCKY_TEST_NONEXISTENT_KEY", h.detail)

    def test_empty_env_value_counts_as_missing(self):
        with mock.patch.dict("os.environ", {"BUCKY_TEST_EMPTY_KEY": "  "}):
            adapter = ProviderAdapter(_entry(env_keys=["BUCKY_TEST_EMPTY_KEY"]))
            self.assertEqual(adapter.healthcheck().status, HEALTH_DISABLED)

    def test_env_key_present_returns_ok(self):
        with mock.patch.dict("os.environ", {"BUCKY_TEST_SET_KEY": "value"}):
            adapter = ProviderAdapter(_entry(env_keys=["BUCKY_TEST_SET_KEY"]))
            self.assertEqual(adapter.healthcheck().status, HEALTH_OK)

    def test_non_list_env_keys_no_crash(self):
        adapter = ProviderAdapter(_entry(env_keys="not-a-list"))
        self.assertEqual(adapter.healthcheck().status, HEALTH_OK)

    def test_non_dict_entry_no_crash(self):
        adapter = ProviderAdapter("garbage")
        self.assertEqual(adapter.healthcheck().status, HEALTH_DISABLED)

    def test_probe_exception_returns_failed(self):
        class Boom(ProviderAdapter):
            name = "boom"

            def _probe(self):
                raise RuntimeError("폭발")

        h = Boom(_entry()).healthcheck()
        self.assertEqual(h.status, HEALTH_FAILED)
        self.assertIn("폭발", h.detail)


class CliMissingTests(unittest.TestCase):
    """CLI 없음 → healthcheck failed (플랜 §Stage 6 계약)."""

    def test_claude_cli_missing_returns_failed(self):
        with mock.patch.dict("os.environ", {"CLAUDE_COMMAND": MISSING_EXE}):
            h = ClaudeCliAdapter(_entry()).healthcheck()
        self.assertEqual(h.status, HEALTH_FAILED)
        self.assertIn("CLI 없음", h.detail)

    def test_codex_cli_missing_returns_failed(self):
        with mock.patch.dict("os.environ", {"CODEX_COMMAND": MISSING_EXE}):
            h = CodexCliAdapter(_entry()).healthcheck()
        self.assertEqual(h.status, HEALTH_FAILED)


class RunGuardTests(unittest.TestCase):
    """run()은 어떤 입력에도 예외 없이 AgentResult를 반환한다."""

    def _ok_adapter(self) -> ProviderAdapter:
        return ProviderAdapter(_entry())

    def test_disabled_adapter_run_returns_failed(self):
        res = ProviderAdapter(_entry(enabled=False)).run(VALID_SPEC, "지시문")
        self.assertEqual(res.status, "failed")
        self.assertIn("실행 불가", res.summary)

    def test_empty_instruction_returns_failed(self):
        res = self._ok_adapter().run(VALID_SPEC, "")
        self.assertEqual(res.status, "failed")
        self.assertIn("instruction", res.summary)

    def test_non_string_instruction_returns_failed(self):
        res = self._ok_adapter().run(VALID_SPEC, None)
        self.assertEqual(res.status, "failed")

    def test_invalid_task_spec_returns_failed(self):
        bad = TaskSpec(task_id="nope", task_type="code")
        res = self._ok_adapter().run(bad, "지시문")
        self.assertEqual(res.status, "failed")
        self.assertIn("TaskSpec", res.summary)

    def test_non_task_spec_returns_failed(self):
        res = self._ok_adapter().run({"task_id": "x"}, "지시문")
        self.assertEqual(res.status, "failed")

    def test_execute_exception_returns_failed(self):
        class Boom(ProviderAdapter):
            name = "boom"

            def _execute(self, task_spec, instruction):
                raise RuntimeError("실행 중 폭발")

        res = Boom(_entry()).run(VALID_SPEC, "지시문")
        self.assertEqual(res.status, "failed")
        self.assertIn("실행 중 폭발", res.summary)

    def test_base_execute_is_stub(self):
        res = self._ok_adapter().run(VALID_SPEC, "지시문")
        self.assertEqual(res.status, "failed")
        self.assertIn("stub", res.summary)

    def test_run_result_is_valid_agent_result(self):
        res = self._ok_adapter().run(VALID_SPEC, "")
        self.assertIsInstance(res, AgentResult)
        self.assertEqual(res.validate(), [])


class EstimateTests(unittest.TestCase):
    def test_disabled_estimate_not_ok(self):
        est = ProviderAdapter(_entry(enabled=False)).estimate(VALID_SPEC)
        self.assertFalse(est.ok)

    def test_invalid_spec_estimate_not_ok(self):
        est = ProviderAdapter(_entry()).estimate(TaskSpec(task_id="nope", task_type=""))
        self.assertFalse(est.ok)

    def test_default_model_resolves_alias(self):
        entry = _entry(models={"default": "gemini-2.0-flash"}, default_model="default")
        self.assertEqual(ProviderAdapter(entry).default_model(), "gemini-2.0-flash")

    def test_default_model_without_models_map(self):
        self.assertEqual(ProviderAdapter(_entry(default_model="sonnet")).default_model(), "sonnet")

    def test_claude_estimate_uses_model_router(self):
        with mock.patch("bucky_client.is_bucky_available", return_value=True):
            est = ClaudeCliAdapter(_entry()).estimate(VALID_SPEC)
        self.assertTrue(est.ok)
        self.assertTrue(est.model, "task_type=code 라우팅 모델이 비어 있음")

    def test_base_stub_estimate_not_ok(self):
        """실행이 stub인 어댑터는 healthy여도 estimate ok=False (run과 모순 금지)."""
        est = ProviderAdapter(_entry()).estimate(VALID_SPEC)
        self.assertFalse(est.ok)
        self.assertIn("실행 미지원", est.detail)

    def test_codex_stub_estimate_not_ok_even_when_healthy(self):
        with mock.patch("bucky_client.is_codex_available", return_value=True):
            est = CodexCliAdapter(_entry()).estimate(VALID_SPEC)
        self.assertFalse(est.ok)

    def test_gemini_stub_estimate_not_ok_even_when_healthy(self):
        ok = Health("gemini", HEALTH_OK)
        with mock.patch.object(GeminiAdapter, "_probe", return_value=ok):
            est = GeminiAdapter(_entry()).estimate(VALID_SPEC)
        self.assertFalse(est.ok)


class ClaudeRunWiringTests(unittest.TestCase):
    """claude_cli_adapter가 bucky_client를 호환 래핑하는지 (실호출 없이 mock)."""

    def test_run_delegates_to_run_bucky(self):
        with mock.patch("bucky_client.is_bucky_available", return_value=True), \
             mock.patch("bucky_client.run_bucky", return_value="응답 텍스트") as m:
            res = ClaudeCliAdapter(_entry()).run(VALID_SPEC, "지시문")
        self.assertEqual(res.status, "completed")
        self.assertEqual(res.summary, "응답 텍스트")
        self.assertEqual(res.validate(), [])
        m.assert_called_once_with("지시문", task_type="code")

    def test_run_bucky_error_becomes_failed_result(self):
        import bucky_client

        with mock.patch("bucky_client.is_bucky_available", return_value=True), \
             mock.patch("bucky_client.run_bucky", side_effect=bucky_client.BuckyError("한도 초과")):
            res = ClaudeCliAdapter(_entry()).run(VALID_SPEC, "지시문")
        self.assertEqual(res.status, "failed")
        self.assertIn("한도 초과", res.summary)


class StubAdapterTests(unittest.TestCase):
    """stub 어댑터는 healthy여도 run이 failed stub을 반환한다 (실연동 최소화)."""

    def test_codex_run_is_stub(self):
        with mock.patch("bucky_client.is_codex_available", return_value=True):
            res = CodexCliAdapter(_entry()).run(VALID_SPEC, "지시문")
        self.assertEqual(res.status, "failed")
        self.assertIn("독립 검수 전용", res.summary)

    def test_gemini_run_is_stub(self):
        ok = Health("gemini", HEALTH_OK)
        with mock.patch.object(GeminiAdapter, "_probe", return_value=ok):
            res = GeminiAdapter(_entry()).run(VALID_SPEC, "지시문")
        self.assertEqual(res.status, "failed")
        self.assertIn("stub", res.summary)


if __name__ == "__main__":
    unittest.main()
