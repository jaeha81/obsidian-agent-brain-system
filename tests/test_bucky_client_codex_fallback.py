import importlib
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


class BuckyClientCodexFallbackTests(unittest.TestCase):
    def setUp(self):
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        sys.modules.pop("bucky_client", None)
        self.client = importlib.import_module("bucky_client")

    def tearDown(self):
        os.environ.pop("BUCKY_CODEX_ON_LIMIT", None)
        os.environ.pop("CODEX_SANDBOX", None)

    def test_run_bucky_falls_back_to_codex_when_claude_subscription_limit_is_hit(self):
        os.environ["BUCKY_CODEX_ON_LIMIT"] = "1"
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            if cmd[0] == "claude":
                return SimpleNamespace(
                    returncode=1,
                    stdout="",
                    stderr="Claude AI usage limit reached. Try again later.",
                )
            return SimpleNamespace(returncode=0, stdout="codex stdout", stderr="")

        with (
            patch.object(self.client, "is_bucky_available", return_value=True),
            patch.object(self.client, "bucky_command", return_value="claude"),
            patch.object(self.client, "is_codex_available", return_value=True),
            patch.object(self.client, "codex_command", return_value="codex"),
            patch.object(self.client, "fallback_chain", return_value=["sonnet"]),
            patch.object(self.client.subprocess, "run", side_effect=fake_run),
            patch("tempfile.NamedTemporaryFile") as named_temp,
        ):
            named_temp.return_value.__enter__.return_value.name = str(Path(os.getenv("TEMP", ".")) / "codex-out.md")
            Path(named_temp.return_value.__enter__.return_value.name).write_text("codex fallback answer", encoding="utf-8")

            result = self.client.run_bucky("작업 계속해줘")

        self.assertEqual(result, "codex fallback answer")
        self.assertEqual(calls[0][0], "claude")
        self.assertEqual(calls[1][0], "codex")
        self.assertIn("exec", calls[1])

    def test_run_bucky_falls_back_to_codex_when_claude_extra_usage_is_out(self):
        os.environ["BUCKY_CODEX_ON_LIMIT"] = "1"
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            if cmd[0] == "claude":
                return SimpleNamespace(
                    returncode=1,
                    stdout="",
                    stderr="You're out of extra usage · resets 3:40am (Asia/Seoul)",
                )
            return SimpleNamespace(returncode=0, stdout="codex stdout", stderr="")

        output_path = Path(os.getenv("TEMP", ".")) / "codex-extra-usage-out.md"
        output_path.write_text("codex extra usage fallback answer", encoding="utf-8")

        with (
            patch.object(self.client, "is_bucky_available", return_value=True),
            patch.object(self.client, "bucky_command", return_value="claude"),
            patch.object(self.client, "is_codex_available", return_value=True),
            patch.object(self.client, "codex_command", return_value="codex"),
            patch.object(self.client, "fallback_chain", return_value=["sonnet"]),
            patch.object(self.client.subprocess, "run", side_effect=fake_run),
            patch("tempfile.NamedTemporaryFile") as named_temp,
        ):
            named_temp.return_value.__enter__.return_value.name = str(output_path)

            result = self.client.run_bucky("계속 진행")

        self.assertEqual(result, "codex extra usage fallback answer")
        self.assertEqual(calls[1][0], "codex")

    def test_run_bucky_with_tools_uses_writable_codex_sandbox_on_limit(self):
        os.environ["BUCKY_CODEX_ON_LIMIT"] = "1"
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            if cmd[0] == "claude":
                return SimpleNamespace(returncode=1, stdout="", stderr="subscription limit exceeded")
            return SimpleNamespace(returncode=0, stdout="codex stdout", stderr="")

        output_path = Path(os.getenv("TEMP", ".")) / "codex-tools-out.md"
        output_path.write_text("codex tool fallback answer", encoding="utf-8")

        with (
            patch.object(self.client, "is_bucky_available", return_value=True),
            patch.object(self.client, "bucky_command", return_value="claude"),
            patch.object(self.client, "is_codex_available", return_value=True),
            patch.object(self.client, "codex_command", return_value="codex"),
            patch.object(self.client, "fallback_chain", return_value=["sonnet"]),
            patch.object(self.client.subprocess, "run", side_effect=fake_run),
            patch("tempfile.NamedTemporaryFile") as named_temp,
        ):
            named_temp.return_value.__enter__.return_value.name = str(output_path)

            result = self.client.run_bucky_with_tools("파일 수정 작업")

        self.assertEqual(result, "codex tool fallback answer")
        codex_call = calls[1]
        self.assertEqual(codex_call[codex_call.index("--sandbox") + 1], "workspace-write")

    def test_limit_message_in_stdout_with_noise_stderr_still_falls_back(self):
        """한도 메시지가 stdout에만 있고 stderr에 무관 텍스트가 있어도 폴백된다 (결합 판정)."""
        os.environ["BUCKY_CODEX_ON_LIMIT"] = "1"
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            if cmd[0] == "claude":
                return SimpleNamespace(
                    returncode=1,
                    stdout="Claude AI usage limit reached.",
                    stderr="warning: telemetry disabled",
                )
            return SimpleNamespace(returncode=0, stdout="codex stdout", stderr="")

        output_path = Path(os.getenv("TEMP", ".")) / "codex-stdout-limit-out.md"
        output_path.write_text("codex stdout limit fallback answer", encoding="utf-8")

        with (
            patch.object(self.client, "is_bucky_available", return_value=True),
            patch.object(self.client, "bucky_command", return_value="claude"),
            patch.object(self.client, "is_codex_available", return_value=True),
            patch.object(self.client, "codex_command", return_value="codex"),
            patch.object(self.client, "fallback_chain", return_value=["sonnet"]),
            patch.object(self.client.subprocess, "run", side_effect=fake_run),
            patch("tempfile.NamedTemporaryFile") as named_temp,
        ):
            named_temp.return_value.__enter__.return_value.name = str(output_path)

            result = self.client.run_bucky("작업 계속해줘")

        self.assertEqual(result, "codex stdout limit fallback answer")
        self.assertEqual(calls[1][0], "codex")

    def test_generic_error_does_not_fall_back_to_codex(self):
        """한도가 아닌 일반 실패(포트 번호 4290 등)는 BuckyError — Codex 폴백 금지."""
        os.environ["BUCKY_CODEX_ON_LIMIT"] = "1"
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return SimpleNamespace(
                returncode=1,
                stdout="",
                stderr="connection refused on port 4290",
            )

        with (
            patch.object(self.client, "is_bucky_available", return_value=True),
            patch.object(self.client, "bucky_command", return_value="claude"),
            patch.object(self.client, "fallback_chain", return_value=["sonnet"]),
            patch.object(self.client.subprocess, "run", side_effect=fake_run),
        ):
            with self.assertRaises(self.client.BuckyError) as ctx:
                self.client.run_bucky("작업")

        self.assertNotIsInstance(ctx.exception, self.client.BuckyLimitError)
        self.assertTrue(all(cmd[0] == "claude" for cmd in calls), "codex가 호출되면 안 됨")


class LimitPatternTests(unittest.TestCase):
    """LIMIT_PATTERNS 정탐/오탐 고정 — 실제 한도 메시지는 잡고 유사 텍스트는 통과시킨다."""

    def setUp(self):
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        sys.modules.pop("bucky_client", None)
        self.client = importlib.import_module("bucky_client")

    def test_real_limit_messages_match(self):
        for text in (
            "Claude AI usage limit reached. Try again later.",
            "You're out of extra usage · resets 3:40am (Asia/Seoul)",
            "5-hour limit reached ∙ resets 4am",
            "API Error: 429 too many requests",
            "HTTP 429",
            "rate limit exceeded",
            "사용 한도 초과",
        ):
            self.assertTrue(self.client.LIMIT_PATTERNS.search(text), f"매치 실패: {text!r}")

    def test_similar_but_unrelated_text_does_not_match(self):
        for text in (
            "connection refused on port 4290",
            "listening on port 429",
            "cache resets at 10am",
            "the program resets tomorrow",
            "processed 4290 rows",
        ):
            self.assertFalse(self.client.LIMIT_PATTERNS.search(text), f"오탐: {text!r}")


if __name__ == "__main__":
    unittest.main()
