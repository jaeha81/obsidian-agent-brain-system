import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.subscription_roi import (
    AgentReport,
    collect_cli_usage_state,
    efficiency_signals,
    resolve_quota,
    summarize_usage,
    usage_recommendation,
    window_distribution,
)
from scripts.generate_ai_usage_dashboard import render_dashboard

KST = timezone(timedelta(hours=9))


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

    def test_window_distribution_buckets_events_into_reset_windows(self):
        now = datetime(2026, 6, 21, 12, 0, tzinfo=KST)
        # current window [07:00, 12:00); previous [02:00, 07:00)
        events = [
            datetime(2026, 6, 21, 11, 0, tzinfo=KST),  # current
            datetime(2026, 6, 21, 5, 0, tzinfo=KST),   # previous
            datetime(2026, 6, 21, 3, 0, tzinfo=KST),   # previous
        ]
        windows = window_distribution(events, reset_hours=5, now=now, lookback_windows=8)

        self.assertEqual(len(windows), 8)
        self.assertTrue(windows[-1]["is_current"])
        self.assertEqual(windows[-1]["count"], 1)   # current window
        self.assertEqual(windows[-2]["count"], 2)   # previous window

    def test_efficiency_signals_model_mix_and_limit_risk(self):
        now = datetime(2026, 6, 21, 12, 0, tzinfo=KST)
        claude = AgentReport(name="Claude Code")
        claude.add_session("2026-06-21", 4, 100, 50, 10, [now - timedelta(minutes=20)])
        codex = AgentReport(name="Codex")
        codex.add_session("2026-06-21", 2, 80, 30, 0, [now - timedelta(minutes=15)])
        cli_state = {
            "models": {"haiku": {"calls": 3}, "sonnet": {"calls": 1}},
            "limit_events": 1,
            "limit_event_times": [now - timedelta(minutes=30)],
            "latest_limit_event": {"timestamp": (now - timedelta(minutes=30)).isoformat()},
        }

        signals = efficiency_signals(claude, codex, cli_state, reset_hours=5, now=now)

        self.assertEqual(signals["model_mix"]["percent"]["haiku"], 75.0)
        self.assertEqual(signals["model_mix"]["percent"]["sonnet"], 25.0)
        self.assertEqual(signals["status"], "LIMIT-RISK")
        self.assertEqual(signals["per_agent"]["Claude Code"]["status"], "LIMIT-RISK")
        self.assertEqual(signals["limit_frequency"]["recent"], 1)

    def test_efficiency_signals_flags_idle_when_current_window_empty(self):
        now = datetime(2026, 6, 21, 12, 0, tzinfo=KST)
        claude = AgentReport(name="Claude Code")
        # five events in an older window, none in the current window
        old = datetime(2026, 6, 21, 1, 0, tzinfo=KST)
        claude.add_session("2026-06-21", 5, 100, 50, 10, [old] * 5)
        codex = AgentReport(name="Codex")

        signals = efficiency_signals(claude, codex, {}, reset_hours=5, now=now)

        self.assertEqual(signals["per_agent"]["Claude Code"]["status"], "IDLE")
        self.assertTrue(signals["per_agent"]["Claude Code"]["idle"])

    def test_resolve_quota_auto_then_manual_then_none(self):
        now = datetime(2026, 6, 21, 12, 0, tzinfo=KST)
        cli_state = {
            "latest_limit_event": {
                "timestamp": (now - timedelta(hours=1)).isoformat(),
                "detail": "out of usage",
            }
        }
        missing = Path(tempfile.gettempdir()) / "no_such_quota_override_xyz.json"

        # auto only
        auto = resolve_quota(cli_state, reset_hours=5, now=now, override_path=missing)
        self.assertEqual(auto["Claude Code"]["source"], "estimated")
        self.assertIsNotNone(auto["Claude Code"]["reset_at"])
        self.assertIsNone(auto["Codex"]["source"])

        # manual override wins
        with tempfile.TemporaryDirectory() as td:
            override = Path(td) / "ai_usage_quota.json"
            override.write_text(
                json.dumps(
                    {
                        "Claude Code": {
                            "reset_at": "2026-06-21T14:00:00+09:00",
                            "limit_status": "5h 창 80% 소진",
                        }
                    }
                ),
                encoding="utf-8",
            )
            manual = resolve_quota(cli_state, reset_hours=5, now=now, override_path=override)
            self.assertEqual(manual["Claude Code"]["source"], "manual")
            self.assertEqual(manual["Claude Code"]["limit_status"], "5h 창 80% 소진")

        # neither auto nor manual
        none = resolve_quota({}, reset_hours=5, now=now, override_path=missing)
        self.assertIsNone(none["Claude Code"]["source"])
        self.assertIsNone(none["Codex"]["source"])

    def test_render_dashboard_includes_gauge_charts_and_status(self):
        now = datetime(2026, 6, 21, 12, 0, tzinfo=KST)
        claude = AgentReport(name="Claude Code")
        claude.add_session("2026-06-21", 20, 1000, 500, 250, [now - timedelta(minutes=10)])
        codex = AgentReport(name="Codex")
        codex.add_session("2026-06-21", 10, 800, 300, 0, [now - timedelta(minutes=5)])
        usage_state = {
            "total_calls": 4,
            "limit_events": 0,
            "limit_event_times": [],
            "recommended_claude_model": "sonnet",
            "latest_limit_event": None,
            "models": {"haiku": {"calls": 3, "successes": 3, "failures": 0},
                       "sonnet": {"calls": 1, "successes": 1, "failures": 0}},
        }

        html = render_dashboard(
            reports=[claude, codex],
            days=1,
            generated_at="2026-06-21 12:00 KST",
            reset_hours=5,
            usage_state=usage_state,
            now=now,
        )

        self.assertIn("효율 신호", html)
        self.assertIn("모델 믹스", html)
        self.assertIn("지금 할 것", html)
        self.assertIn("현재창 부하", html)
        self.assertIn("실토큰", html)
        self.assertNotIn("목표 사용률", html)


if __name__ == "__main__":
    unittest.main()
