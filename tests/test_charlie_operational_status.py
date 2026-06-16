import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


class CharlieOperationalStatusTests(unittest.TestCase):
    def test_status_contains_runtime_and_user_confirmation_checks(self):
        import charlie_audit

        status = charlie_audit.build_status()

        self.assertIn("runtime_status", status)
        self.assertIn("operational_checks", status)
        check_ids = {check["id"] for check in status["operational_checks"]}
        self.assertEqual(
            check_ids,
            {
                "discord_bucky_live",
                "discord_channel_routes",
                "charlie_pc_status",
                "daily_plus_automation",
                "development_instruction_guard",
                "charlie_dashboard_realtime",
                "charlie_dashboard_detail",
                "pc_anomaly_reporting",
                "charlie_exception_only",
            },
        )

    def test_dashboard_polls_status_json_and_renders_operational_sections(self):
        html = (ROOT / "docs" / "charlie-system-audit.html").read_text(encoding="utf-8")

        self.assertIn("setInterval(load", html)
        self.assertIn("operationalChecks", html)
        self.assertIn("runtimeStatus", html)
        self.assertIn("empty Charlie status", html)

    def test_runtime_pid_file_must_match_running_python_process(self):
        import charlie_audit

        runtime_status = {
            "bucky_health": {"ok": True},
            "bot_pid_file": {
                "exists": True,
                "valid": True,
                "pid": 12345,
                "process_match": False,
                "path": "ObsidianVault\\10_AgentBus\\signals\\bucky_bot.pid",
            },
            "discord_err": {"exists": True, "age_seconds": 1},
            "daily_plus_bridge": {"latest_outbox": "today.md", "latest_outbox_sent": True},
            "daily_plus_dashboard": {"latest_date": "2026-06-16"},
        }

        findings = charlie_audit.check_runtime_findings(runtime_status)
        self.assertTrue(any("PID" in finding.title for finding in findings))

        checks = charlie_audit.build_operational_checks(runtime_status)
        live_check = next(check for check in checks if check["id"] == "discord_bucky_live")
        self.assertEqual(live_check["status"], "WARNING")

    def test_discord_live_check_uses_bot_runtime_markers_not_local_health(self):
        import charlie_audit

        runtime_status = {
            "bucky_health": {"ok": False},
            "bot_pid_file": {"exists": True, "valid": True, "pid": 12345, "process_match": True},
            "discord_err": {
                "exists": True,
                "age_seconds": 1,
                "markers": {
                    "Bot ready": True,
                    "IntakeConsumer": True,
                    "DailyPlusBridge": True,
                    "Traceback": False,
                    "ERROR": False,
                },
            },
            "daily_plus_bridge": {"latest_outbox": "today.md", "latest_outbox_sent": True},
            "daily_plus_dashboard": {"latest_date": "2026-06-16"},
        }

        checks = charlie_audit.build_operational_checks(runtime_status)
        live_check = next(check for check in checks if check["id"] == "discord_bucky_live")
        self.assertEqual(live_check["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
