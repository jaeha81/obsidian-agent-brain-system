import sys
import tempfile
import unittest
import os
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import agentbus_queue_audit


class AgentBusQueueAuditTests(unittest.TestCase):
    def test_audit_counts_known_queue_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            bus = Path(tmp) / "10_AgentBus"
            (bus / "inbox").mkdir(parents=True)
            (bus / "completed").mkdir()
            (bus / "failed").mkdir()
            (bus / "inbox" / "a.md").write_text("a", encoding="utf-8")
            (bus / "inbox" / "b.md").write_text("b", encoding="utf-8")
            (bus / "failed" / "bad.md").write_text("bad", encoding="utf-8")

            report = agentbus_queue_audit.audit_agentbus(bus)

            self.assertEqual(report["queues"]["inbox"]["count"], 2)
            self.assertEqual(report["queues"]["completed"]["count"], 0)
            self.assertEqual(report["queues"]["failed"]["count"], 1)
            self.assertEqual(report["total_files"], 3)

    def test_audit_marks_large_inbox_as_attention_needed(self):
        with tempfile.TemporaryDirectory() as tmp:
            bus = Path(tmp) / "10_AgentBus"
            (bus / "inbox").mkdir(parents=True)
            for i in range(6):
                (bus / "inbox" / f"{i}.md").write_text("x", encoding="utf-8")

            report = agentbus_queue_audit.audit_agentbus(bus, inbox_attention_threshold=5)

            self.assertIn("inbox_over_threshold", report["warnings"])
            self.assertEqual(report["runtime_risk"], "warning")

    def test_build_triage_manifest_classifies_without_moving_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            bus = Path(tmp) / "10_AgentBus"
            for rel in ("inbox", "completed", "failed"):
                (bus / rel).mkdir(parents=True)
            old_inbox = bus / "inbox" / "old.md"
            new_inbox = bus / "inbox" / "new.md"
            done = bus / "completed" / "done.md"
            failed = bus / "failed" / "bad.md"
            for path in (old_inbox, new_inbox, done, failed):
                path.write_text(path.name, encoding="utf-8")

            now = time.time()
            os.utime(old_inbox, (now - 10 * 86400, now - 10 * 86400))
            os.utime(new_inbox, (now, now))

            manifest = agentbus_queue_audit.build_triage_manifest(
                bus,
                now=now,
                active_days=3,
            )

            by_name = {entry["name"]: entry for entry in manifest}
            self.assertEqual(by_name["old.md"]["decision"], "historical_residue")
            self.assertEqual(by_name["new.md"]["decision"], "active_candidate")
            self.assertEqual(by_name["done.md"]["decision"], "historical_completed")
            self.assertEqual(by_name["bad.md"]["decision"], "failed_review")
            self.assertTrue(old_inbox.exists())

    def test_write_triage_manifest_csv_writes_header_and_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "manifest.csv"
            entries = [{
                "queue": "inbox",
                "name": "a.md",
                "decision": "active_candidate",
                "age_days": 0,
                "path": "x/a.md",
            }]

            agentbus_queue_audit.write_triage_manifest_csv(entries, out)

            text = out.read_text(encoding="utf-8")
            self.assertIn("queue,name,decision,age_days,path", text)
            self.assertIn("inbox,a.md,active_candidate,0,x/a.md", text)


if __name__ == "__main__":
    unittest.main()
