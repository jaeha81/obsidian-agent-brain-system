import sys
import unittest
from pathlib import Path
from unittest import mock

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import bucky_worker_pool as wp  # noqa: E402
from core.agent_result import AgentResult  # noqa: E402


class ProviderFallbackTests(unittest.IsolatedAsyncioTestCase):
    """claude_code(run_bucky) 소진 후 'bucky' 대화 태스크의 provider 폴백 배선 확인.

    claude_code/codex_pro는 스킵하고(도구 미지원 provider로 대체 불가), 나머지 후보만 시도한다.
    """

    async def test_skips_claude_and_codex_uses_next_provider(self):
        pool = wp.WorkerPool()
        ok_result = AgentResult(agent="gemini", status="completed", summary="게미니 응답")
        gemini_adapter = mock.Mock()
        gemini_adapter.run.return_value = ok_result

        with mock.patch.object(wp, "provider_candidates", return_value=["claude_code", "codex_pro", "gemini"]), \
             mock.patch.object(wp, "get_adapter", side_effect=lambda name: gemini_adapter if name == "gemini" else None):
            result = await pool._try_provider_fallback("T001", "제목", "안녕", None)

        self.assertIsNotNone(result)
        self.assertIn("gemini 폴백", result)
        self.assertIn("게미니 응답", result)
        gemini_adapter.run.assert_called_once()

    async def test_returns_none_when_no_fallback_succeeds(self):
        pool = wp.WorkerPool()
        failed_result = AgentResult(agent="gemini", status="failed", summary="키 없음")
        gemini_adapter = mock.Mock()
        gemini_adapter.run.return_value = failed_result

        with mock.patch.object(wp, "provider_candidates", return_value=["claude_code", "gemini"]), \
             mock.patch.object(wp, "get_adapter", return_value=gemini_adapter):
            result = await pool._try_provider_fallback("T002", "제목", "안녕", None)

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
