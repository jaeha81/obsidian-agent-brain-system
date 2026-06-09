import tempfile
import unittest
from pathlib import Path

from scripts.subscription_roi import AgentReport, collect_cli_usage_state, summarize_usage, usage_recommendation
from scripts.generate_ai_usage_dashboard import render_dashboard


class SubscriptionRoiTests(unittest.TestCase):
    def test_summarize_usage_calculates_cost_and_reset_utilization(self):
        report = AgentReport(name="Claude Code")
        report.add_session("2026-06-01", 12, 1000, 300, 200)
        report.add_session("2026-06-02", 8, 700, 200, 100)

        summary = summarize_usage(report, days=2, monthly_usd=100, reset_hours=5, target_sessions_per_reset=2)

        self.assertEqual(summary["agent"], "Claude Code")
        self.assertEqual(summary["sessions"], 2)
        self.assertEqual(summary["messages"], 20)
        self.assertAlmostEqual(summary["prorated_budget_usd"], 6.67, places=2)
        self.assertAlmostEqual(summary["cost_per_session_usd"], 3.33, places=2)
        self.assertEqual(summary["reset_windows"], 10)
        self.assertEqual(summary["target_sessions"], 20)
        self.assertEqual(summary["session_utilization_percent"], 10.0)

    def test_usage_recommendation_flags_underuse_and_interruption_plan(self):
        underused = {
            "session_utilization_percent": 12,
            "active_day_percent": 25,
            "cost_per_session_usd": 8.0,
        }

        text = usage_recommendation("Codex", underused)

        self.assertIn("UNDERUSED", text)
        self.assertIn("review", text.lower())
        self.assertIn("handoff", text.lower())

    def test_render_dashboard_contains_operational_markers(self):
        claude = AgentReport(name="Claude Code")
        claude.add_session("2026-06-01", 20, 1000, 500, 250)
        codex = AgentReport(name="Codex")
        codex.add_session("2026-06-01", 10, 800, 300, 100)

        html = render_dashboard(
            reports=[claude, codex],
            days=1,
            generated_at="2026-06-03 10:00 KST",
            reset_hours=5,
        )

        self.assertIn("AI Usage", html)
        self.assertIn("Claude Code", html)
        self.assertIn("Codex", html)
        self.assertIn("reset window", html)
        self.assertIn("handoff", html)

    def test_collect_cli_usage_state_detects_model_failures_and_reset(self):
        with tempfile.TemporaryDirectory() as td:
            log_path = Path(td) / "cli-tools.jsonl"
            log_path.write_text(
                "\n".join(
                    [
                        '{"timestamp":"2026-06-10T02:50:00","command":"claude","model":"sonnet","task_type":"chat","source":"run_bucky","success":false,"duration_ms":5000,"prompt_summary":"큰 작업","response_summary":"You are out of extra usage · resets 3:40am (Asia/Seoul)"}',
                        '{"timestamp":"2026-06-10T02:51:00","command":"claude","model":"haiku","task_type":"classify","source":"run_bucky","success":true,"duration_ms":900,"prompt_summary":"분류","response_summary":"ok"}',
                        '{"timestamp":"2026-06-10T02:52:00","command":"codex","model":"codex-default","task_type":"review","source":"run_bucky_codex_on_limit","success":true,"duration_ms":1200,"prompt_summary":"검수","response_summary":"ok"}',
                    ]
                ),
                encoding="utf-8",
            )

            state = collect_cli_usage_state(log_path)

        self.assertEqual(state["total_calls"], 3)
        self.assertEqual(state["models"]["sonnet"]["failures"], 1)
        self.assertEqual(state["models"]["haiku"]["successes"], 1)
        self.assertEqual(state["models"]["codex-default"]["successes"], 1)
        self.assertIn("resets 3:40am", state["latest_limit_event"]["detail"])
        self.assertEqual(state["recommended_claude_model"], "haiku")

    def test_render_dashboard_includes_real_cli_state_and_haiku_policy(self):
        claude = AgentReport(name="Claude Code")
        codex = AgentReport(name="Codex")
        usage_state = {
            "total_calls": 3,
            "limit_events": 1,
            "recommended_claude_model": "haiku",
            "latest_limit_event": {
                "timestamp": "2026-06-10T02:50:00",
                "model": "sonnet",
                "detail": "You are out of extra usage · resets 3:40am (Asia/Seoul)",
            },
            "models": {
                "sonnet": {"calls": 1, "successes": 0, "failures": 1},
                "haiku": {"calls": 1, "successes": 1, "failures": 0},
                "codex-default": {"calls": 1, "successes": 1, "failures": 0},
            },
        }

        html = render_dashboard(
            reports=[claude, codex],
            days=1,
            generated_at="2026-06-10 03:00 KST",
            reset_hours=5,
            usage_state=usage_state,
        )

        self.assertIn("실제 감지 상태", html)
        self.assertIn("You are out of extra usage", html)
        self.assertIn("Haiku 우선", html)
        self.assertIn("Sonnet 절약", html)


if __name__ == "__main__":
    unittest.main()
