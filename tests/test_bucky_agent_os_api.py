import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

from flask import Flask


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


class BuckyAgentOsApiTests(unittest.TestCase):
    def setUp(self):
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))

        import bucky_agent_os_api as api

        self.api = api
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

        self.memory_db = self.tmp_path / "bucky_memory.db"
        conn = sqlite3.connect(self.memory_db)
        conn.execute(
            "CREATE TABLE learned_facts (id INTEGER PRIMARY KEY, category TEXT, fact TEXT, source TEXT, ts TEXT)"
        )
        conn.execute(
            "CREATE TABLE sessions (id INTEGER PRIMARY KEY, channel TEXT, started TEXT, ended TEXT, external_key TEXT, label TEXT)"
        )
        conn.execute(
            "CREATE TABLE conv_history (id INTEGER PRIMARY KEY, channel TEXT, role TEXT, content TEXT, ts TEXT, session_id INTEGER)"
        )
        conn.execute(
            "INSERT INTO learned_facts(category, fact, source, ts) VALUES (?, ?, ?, ?)",
            ("goal", "Keep Bucky dashboard state observable.", "test", "2026-06-10T01:00:00"),
        )
        conn.execute(
            "INSERT INTO sessions(channel, started, ended, external_key, label) VALUES (?, ?, ?, ?, ?)",
            ("jh-codex-app", "2026-06-10T01:00:00", "", "agent-os", "Agent OS"),
        )
        conn.execute(
            "INSERT INTO conv_history(channel, role, content, ts, session_id) VALUES (?, ?, ?, ?, ?)",
            ("jh-codex-app", "user", "dashboard check", "2026-06-10T01:05:00", 1),
        )
        conn.commit()
        conn.close()

        self.goal_file = self.tmp_path / "active_goal.json"
        self.goal_file.write_text(
            json.dumps(
                {
                    "goal": "Ship GAP cards",
                    "created": "2026-06-10T01:00:00",
                    "focus": True,
                    "subtasks": [
                        {"id": 1, "body": "Add memory endpoint", "status": "done"},
                        {"id": 2, "body": "Add spend endpoint", "status": "pending"},
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        self.cli_log = self.tmp_path / "cli-tools.jsonl"
        self.cli_log.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "timestamp": "2026-06-10T01:00:00",
                            "model": "sonnet",
                            "success": True,
                            "duration_ms": 1000,
                        }
                    ),
                    json.dumps(
                        {
                            "timestamp": "2026-06-10T01:10:00",
                            "model": "sonnet",
                            "success": False,
                            "response_summary": "subscription limit exceeded",
                        }
                    ),
                ]
            ),
            encoding="utf-8",
        )

        self.old_memory_db = api.MEMORY_DB
        self.old_goal_file = api.ACTIVE_GOAL
        self.old_cli_log = api.CLI_TOOLS_LOG
        api.MEMORY_DB = self.memory_db
        api.ACTIVE_GOAL = self.goal_file
        api.CLI_TOOLS_LOG = self.cli_log

        app = Flask(__name__)
        app.register_blueprint(api.agent_os_bp)
        self.client = app.test_client()

    def tearDown(self):
        self.api.MEMORY_DB = self.old_memory_db
        self.api.ACTIVE_GOAL = self.old_goal_file
        self.api.CLI_TOOLS_LOG = self.old_cli_log
        self.tmp.cleanup()

    def test_memory_endpoint_reports_fact_and_session_counts(self):
        data = self.client.get("/agent-os/memory").get_json()

        self.assertEqual(data["summary"]["fact_count"], 1)
        self.assertEqual(data["summary"]["session_count"], 1)
        # 2026-06-10 4-layer Memory Stack 개편: semantic은 category→[facts] dict
        self.assertIn("goal", data["layers"]["semantic"])
        # short_term이 recent_messages를 대체
        self.assertEqual(data["layers"]["short_term"][0]["channel"], "jh-codex-app")

    def test_goals_endpoint_reports_active_goal_progress(self):
        data = self.client.get("/agent-os/goals").get_json()

        self.assertTrue(data["active"])
        self.assertEqual(data["goal"], "Ship GAP cards")
        self.assertEqual(data["summary"]["done"], 1)
        self.assertEqual(data["summary"]["pending"], 1)
        self.assertEqual(data["summary"]["progress_percent"], 50)

    def test_spend_endpoint_reports_cli_usage_state(self):
        data = self.client.get("/agent-os/spend").get_json()

        self.assertEqual(data["summary"]["total_calls"], 2)
        self.assertEqual(data["summary"]["limit_events"], 1)
        self.assertEqual(data["models"]["sonnet"]["failures"], 1)


if __name__ == "__main__":
    unittest.main()
