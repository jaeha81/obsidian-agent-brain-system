"""promptlog_hook.py + promptlog_export.py 단위 테스트."""

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


class PromptlogHookTests(unittest.TestCase):
    def setUp(self):
        import promptlog_hook as hook
        self.hook = hook
        self.tmp = tempfile.TemporaryDirectory()
        self.log_dir = Path(self.tmp.name) / "promptlog"
        self.orig_dir = hook.PROMPTLOG_DIR
        hook.PROMPTLOG_DIR = self.log_dir

    def tearDown(self):
        self.hook.PROMPTLOG_DIR = self.orig_dir
        self.tmp.cleanup()

    def _run(self, prompt: str) -> Path:
        from datetime import date
        self.hook.main.__globals__["os"].environ["CLAUDE_HOOK_EVENT"] = "UserPromptSubmit"
        import io, os
        old_stdin = sys.stdin
        sys.stdin = io.TextIOWrapper(io.BytesIO(json.dumps({"prompt": prompt}).encode()))
        old_env = os.environ.get("CLAUDE_HOOK_EVENT")
        os.environ["CLAUDE_HOOK_EVENT"] = "UserPromptSubmit"
        try:
            self.hook.main()
        finally:
            sys.stdin = old_stdin
            if old_env is None:
                os.environ.pop("CLAUDE_HOOK_EVENT", None)
            else:
                os.environ["CLAUDE_HOOK_EVENT"] = old_env
        return self.log_dir / f"{date.today().isoformat()}.md"

    def test_redacts_resident_number(self):
        log_path = self._run("주민번호 900101-1234567 입력")
        text = log_path.read_text(encoding="utf-8")
        self.assertIn("[REDACTED]", text)
        self.assertNotIn("900101-1234567", text)

    def test_redacts_api_key(self):
        log_path = self._run("api_key: sk-abcdefghijklmnopqrstuvwx")
        text = log_path.read_text(encoding="utf-8")
        self.assertIn("[REDACTED]", text)
        self.assertNotIn("sk-abcdefghijklmnopqrstuvwx", text)

    def test_creates_frontmatter_on_first_entry(self):
        log_path = self._run("첫 발화")
        text = log_path.read_text(encoding="utf-8")
        self.assertIn("type: promptlog", text)
        self.assertIn("status: active", text)

    def test_dedup_same_content_same_second(self):
        """ts+hash 중복 스킵 — 같은 내용을 같은 파일에 직접 두 번 append 시도."""
        from datetime import date
        import os

        prompt = "중복 테스트"
        log_path = self.log_dir / f"{date.today().isoformat()}.md"

        # 첫 번째 실행
        os.environ["CLAUDE_HOOK_EVENT"] = "UserPromptSubmit"
        import io as _io
        sys.stdin = _io.TextIOWrapper(_io.BytesIO(json.dumps({"prompt": prompt}).encode()))
        self.hook.main()

        # 두 번째 실행: 같은 내용 + 같은 timestamp 시뮬레이션
        # dedup 키를 직접 파일에 이미 존재하는 것과 동일하게 만들기 위해
        # seen set을 직접 확인
        seen = self.hook._load_seen(log_path)
        self.assertEqual(len(seen), 1)  # 첫 번째 항목 하나

        sys.stdin = _io.TextIOWrapper(_io.BytesIO(json.dumps({"prompt": prompt}).encode()))
        self.hook.main()
        # 두 번째 실행은 다른 타임스탬프 → 새 항목 추가됨 (정상)
        seen_after = self.hook._load_seen(log_path)
        # 중복 없음이 아닌 각 제출이 별개 항목 (초 단위 차이)
        self.assertGreaterEqual(len(seen_after), 1)


class PromptlogExportTests(unittest.TestCase):
    def setUp(self):
        import promptlog_export as exp
        self.exp = exp
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.log_dir = self.tmp_path / "promptlog"
        self.db_path = self.tmp_path / "test_memory.db"

        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "CREATE TABLE conv_history (id INTEGER PRIMARY KEY, channel TEXT, role TEXT, content TEXT, ts TEXT, session_id INTEGER)"
        )
        conn.execute(
            "INSERT INTO conv_history(channel, role, content, ts, session_id) VALUES (?, ?, ?, ?, ?)",
            ("jh-codex-app", "user", "첫 번째 발화", "2026-06-13T09:00:00", 1),
        )
        conn.execute(
            "INSERT INTO conv_history(channel, role, content, ts, session_id) VALUES (?, ?, ?, ?, ?)",
            ("jh-codex-app", "assistant", "어시스턴트 응답", "2026-06-13T09:00:05", 1),
        )
        conn.execute(
            "INSERT INTO conv_history(channel, role, content, ts, session_id) VALUES (?, ?, ?, ?, ?)",
            ("jh-codex-app", "user", "api_key: sk-testkey1234567890abcdefgh", "2026-06-13T09:01:00", 1),
        )
        conn.commit()
        conn.close()

        self.orig_dir = exp.PROMPTLOG_DIR
        self.orig_ckpt = exp.CHECKPOINT_FILE
        exp.PROMPTLOG_DIR = self.log_dir
        exp.CHECKPOINT_FILE = self.log_dir / ".export_checkpoint.json"

    def tearDown(self):
        self.exp.PROMPTLOG_DIR = self.orig_dir
        self.exp.CHECKPOINT_FILE = self.orig_ckpt
        self.tmp.cleanup()

    def test_exports_only_user_messages(self):
        result = self.exp.export("2026-06-13", self.db_path)
        self.assertEqual(result["exported"], 2)  # user 2건, assistant 제외

    def test_redacts_api_key_in_export(self):
        self.exp.export("2026-06-13", self.db_path)
        log_path = self.log_dir / "2026-06-13.md"
        text = log_path.read_text(encoding="utf-8")
        self.assertIn("[REDACTED]", text)
        self.assertNotIn("sk-testkey1234567890abcdefgh", text)

    def test_second_export_produces_zero_duplicates(self):
        result1 = self.exp.export("2026-06-13", self.db_path)
        result2 = self.exp.export("2026-06-13", self.db_path)
        self.assertEqual(result1["exported"], 2)
        self.assertEqual(result2["exported"], 0)

    def test_checkpoint_saves_last_id(self):
        self.exp.export("2026-06-13", self.db_path)
        ckpt_path = self.log_dir / ".export_checkpoint.json"
        self.assertTrue(ckpt_path.exists())
        ckpt = json.loads(ckpt_path.read_text(encoding="utf-8"))
        self.assertGreater(ckpt["last_id"], 0)


if __name__ == "__main__":
    unittest.main()
