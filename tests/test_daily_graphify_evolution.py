import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts import daily_graphify_evolution as evolution


class DailyGraphifyEvolutionTests(unittest.TestCase):
    def test_build_summary_links_daily_plus_graph_and_context_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "ObsidianVault"
            report = vault / "10_AgentBus" / "reports" / "20260610_daily_plus_dashboard_report.md"
            graph_report = vault / "graphify-out" / "GRAPH_REPORT.md"
            context_pack = vault / "06_Context_Packs" / "Graphify" / "ObsidianVault_graphify_pack.md"
            report.parent.mkdir(parents=True)
            graph_report.parent.mkdir(parents=True)
            context_pack.parent.mkdir(parents=True)
            report.write_text("status: ready\nToday candidates: `4`\n", encoding="utf-8")
            graph_report.write_text("Nodes: 42\nEdges: 7\nClusters: 3\n", encoding="utf-8")
            context_pack.write_text("# Graphify Context Pack\n", encoding="utf-8")

            summary = evolution.build_graphify_summary(
                root=root,
                date="2026-06-10",
                graph_dir=graph_report.parent,
                context_pack=context_pack,
                bridge_message=Path("ObsidianVault/10_AgentBus/context_requests/graphify/mock.md"),
            )

        self.assertIn("date: 2026-06-10", summary)
        self.assertIn("Daily Plus 09:00 report", summary)
        self.assertIn("Nodes: 42", summary)
        self.assertIn("ObsidianVault/06_Context_Packs/Graphify/ObsidianVault_graphify_pack.md", summary)
        self.assertIn("ObsidianVault/10_AgentBus/context_requests/graphify/mock.md", summary)

    def test_run_skip_graphify_writes_daily_and_latest_agentbus_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "ObsidianVault"
            (vault / "10_AgentBus" / "reports").mkdir(parents=True)
            (vault / "graphify-out").mkdir(parents=True)
            (vault / "10_AgentBus" / "reports" / "20260610_daily_plus_dashboard_report.md").write_text(
                "status: ready\n",
                encoding="utf-8",
            )
            (vault / "graphify-out" / "GRAPH_REPORT.md").write_text("Nodes: 42\nEdges: 7\n", encoding="utf-8")

            bridge_output = (
                "AgentBus message written: "
                + str(vault / "10_AgentBus" / "context_requests" / "graphify" / "mock.md")
            )
            completed = mock.Mock(returncode=0, stdout=bridge_output, stderr="")

            with mock.patch.object(evolution.subprocess, "run", return_value=completed) as run_mock:
                result = evolution.run_daily_graphify_evolution(
                    date="2026-06-10",
                    root=root,
                    skip_graphify=True,
                )

            daily_record = vault / "10_AgentBus" / "completed" / "20260610_daily_graphify_evolution.md"
            latest_record = vault / "10_AgentBus" / "completed" / "latest_daily_graphify_evolution.md"
            self.assertEqual(result, daily_record)
            self.assertTrue(daily_record.exists())
            self.assertEqual(daily_record.read_text(encoding="utf-8"), latest_record.read_text(encoding="utf-8"))
            self.assertIn("context_pack:", daily_record.read_text(encoding="utf-8"))
            self.assertIn("bridge_message:", daily_record.read_text(encoding="utf-8"))
            self.assertEqual(run_mock.call_count, 1)


if __name__ == "__main__":
    unittest.main()
