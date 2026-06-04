import unittest

from scripts.subscription_roi import AgentReport, summarize_usage, usage_recommendation
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


if __name__ == "__main__":
    unittest.main()
