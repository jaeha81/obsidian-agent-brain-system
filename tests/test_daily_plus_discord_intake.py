import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from scripts import discord_bot


class DailyPlusDiscordIntakeTests(unittest.TestCase):
    def test_detects_daily_plus_knowledge_intake_message(self):
        content = "\n".join(
            [
                "!capture https://youtu.be/example",
                "",
                "[Daily Plus Knowledge Intake]",
                "type: link",
                "title: Test video",
                "tags: bucky, youtube",
                "source: daily-plus-dashboard",
                "session_id: daily-plus-intake-20260604-test",
                "follow_up_state: awaiting_user_instruction",
                "files: (none)",
            ]
        )

        payload = discord_bot.parse_daily_plus_intake_content(content)

        self.assertIsNotNone(payload)
        self.assertEqual(payload["capture_target"], "https://youtu.be/example")
        self.assertEqual(payload["type"], "link")
        self.assertEqual(payload["title"], "Test video")
        self.assertEqual(payload["session_id"], "daily-plus-intake-20260604-test")
        self.assertEqual(payload["follow_up_state"], "awaiting_user_instruction")

    def test_builds_session_prompt_with_saved_paths_and_next_wait_state(self):
        payload = {
            "type": "note",
            "title": "User KB memo",
            "tags": "bucky,kb",
            "source": "daily-plus-dashboard",
            "session_id": "daily-plus-intake-20260604-test",
            "follow_up_state": "awaiting_user_instruction",
            "body": "사용자 지식베이스 메모를 분석해줘.",
            "capture_target": "User KB memo",
        }

        prompt = discord_bot.build_daily_plus_intake_session_prompt(
            payload,
            saved_paths=["ObsidianVault/01_RAW/user-kb-memo.md"],
            attachment_paths=["ObsidianVault/01_RAW/Discord/file.pdf"],
        )

        self.assertIn("Daily Plus Knowledge Intake", prompt)
        self.assertIn("session_id: daily-plus-intake-20260604-test", prompt)
        self.assertIn("ObsidianVault/01_RAW/user-kb-memo.md", prompt)
        self.assertIn("ObsidianVault/01_RAW/Discord/file.pdf", prompt)
        self.assertIn("분석 브리핑", prompt)
        self.assertIn("다음 사용자 작업 지시를 기다리는 상태", prompt)

    def test_builds_fallback_reply_that_preserves_utf8_body(self):
        payload = {
            "type": "note",
            "title": "UTF8 smoke",
            "tags": "daily-plus,utf8",
            "source": "daily-plus-dashboard",
            "session_id": "daily-plus-intake-utf8-test",
            "follow_up_state": "awaiting_user_instruction",
            "body": "이 메시지는 UTF-8 한글 검증입니다.",
            "capture_target": "UTF8 smoke",
        }

        reply = discord_bot.build_daily_plus_intake_fallback_reply(
            payload,
            saved_paths=["ObsidianVault/01_RAW/utf8-smoke.md"],
            reason="Bucky CLI timeout",
        )

        self.assertIn("분석 브리핑", reply)
        self.assertIn("이 메시지는 UTF-8 한글 검증입니다.", reply)
        self.assertIn("ObsidianVault/01_RAW/utf8-smoke.md", reply)
        self.assertIn("다음 사용자 작업 지시를 기다리는 상태입니다.", reply)


if __name__ == "__main__":
    unittest.main()
