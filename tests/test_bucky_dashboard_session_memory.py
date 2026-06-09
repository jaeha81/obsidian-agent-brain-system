import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


class BuckyDashboardSessionMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["BUCKY_MEMORY_DB_PATH"] = str(Path(self.tmp.name) / "bucky_memory.db")
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        sys.modules.pop("bucky_memory", None)
        self.mem = importlib.import_module("bucky_memory")

    def tearDown(self):
        conn = getattr(self.mem, "_conn", None)
        if conn is not None:
            conn.close()
            self.mem._conn = None
        self.tmp.cleanup()
        os.environ.pop("BUCKY_MEMORY_DB_PATH", None)

    def test_dashboard_key_reuses_and_reactivates_item_session(self):
        mem = self.mem
        channel = "discord-channel-1"

        dashboard_sid = mem.get_or_create_session_for_key(
            channel,
            "repo:project-a",
            "repo | start | Project A",
        )
        mem.save_message(channel, "user", "dashboard request for Project A")

        other_sid = mem.new_session(channel)
        mem.save_message(channel, "user", "unrelated channel message")
        self.assertEqual(mem.get_active_session(channel), other_sid)

        reused_sid = mem.get_or_create_session_for_key(
            channel,
            "repo:project-a",
            "repo | start | Project A",
        )
        self.assertEqual(reused_sid, dashboard_sid)
        self.assertEqual(mem.get_active_session(channel), dashboard_sid)

        mem.save_message(channel, "user", "follow-up after dashboard send")
        history = mem.load_session_history(channel, dashboard_sid)
        self.assertIn("dashboard request for Project A", [m["content"] for m in history])
        self.assertIn("follow-up after dashboard send", [m["content"] for m in history])

    def test_resume_session_changes_persistent_active_session(self):
        mem = self.mem
        channel = "discord-channel-2"
        first_sid = mem.new_session(channel)
        mem.save_message(channel, "user", "first session message")
        second_sid = mem.new_session(channel)
        mem.save_message(channel, "user", "second session message")

        self.assertTrue(mem.resume_session(channel, first_sid))
        self.assertEqual(mem.get_active_session(channel), first_sid)
        mem.save_message(channel, "user", "continued first session")

        first_history = mem.load_session_history(channel, first_sid)
        second_history = mem.load_session_history(channel, second_sid)
        self.assertIn("continued first session", [m["content"] for m in first_history])
        self.assertNotIn("continued first session", [m["content"] for m in second_history])


class DiscordBotDashboardSessionSourceTests(unittest.TestCase):
    def test_discord_bot_routes_dashboard_payloads_with_session_keys(self):
        src = (SCRIPTS / "discord_bot.py").read_text(encoding="utf-8")
        self.assertIn("def _dashboard_session_key", src)
        self.assertIn("def _activate_dashboard_session", src)
        self.assertIn("session_key=_dashboard_session_key(payload)", src)
        self.assertIn("session_label=_dashboard_session_label(payload)", src)
        self.assertIn("_mem.resume_session", src)
        self.assertIn("voice_channel_id = str(ch.id)", src)
        self.assertIn("await ask_bucky(voice_channel_id, text)", src)
        self.assertNotIn("await ask_bucky(str(self.guild_id), text)", src)


if __name__ == "__main__":
    unittest.main()
