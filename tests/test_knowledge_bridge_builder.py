import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import knowledge_bridge_builder as kbb


def write_note(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


class KnowledgeBridgeBuilderTests(unittest.TestCase):
    def test_build_bridge_notes_connects_operational_sources_to_knowledge_hubs(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "ObsidianVault"
            write_note(vault / "01_RAW" / "capture.md", "Bucky should use Graphify to organize Codex review knowledge.")
            write_note(vault / "10_AgentBus" / "inbox" / "task.md", "Claude Code sent AgentBus status about the JH system.")

            result = kbb.build_knowledge_bridges(vault=vault, limit=10, dry_run=False)

            self.assertEqual(result.created, 2)
            bridge_files = sorted((vault / "03_Knowledge" / "bridges").glob("*.md"))
            self.assertEqual(len(bridge_files), 2)
            merged = "\n".join(path.read_text(encoding="utf-8") for path in bridge_files)
            self.assertIn("[[Bucky]]", merged)
            self.assertIn("[[Graphify]]", merged)
            self.assertIn("[[Codex]]", merged)
            self.assertIn("[[Claude Code]]", merged)
            self.assertIn("[[AgentBus]]", merged)
            self.assertIn("source_path:", merged)

    def test_verify_bridge_notes_fails_when_bridge_has_no_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "ObsidianVault"
            bad_note = vault / "03_Knowledge" / "bridges" / "bad.md"
            write_note(bad_note, "# Bad Bridge\n\nNo links here.")

            failures = kbb.verify_bridge_notes(vault)

            self.assertEqual(failures, [bad_note])

    def test_dry_run_does_not_write_bridge_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "ObsidianVault"
            write_note(vault / "09_Archive" / "session.md", "Graphify and Bucky system evolution notes.")

            result = kbb.build_knowledge_bridges(vault=vault, limit=10, dry_run=True)

            self.assertEqual(result.created, 0)
            self.assertEqual(result.candidates, 1)
            self.assertFalse((vault / "03_Knowledge" / "bridges").exists())

    def test_ensure_hub_notes_creates_missing_functional_hubs(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "ObsidianVault"

            created = kbb.ensure_hub_notes(vault, dry_run=False)

            self.assertIn(vault / "03_Knowledge" / "hubs" / "Graphify.md", created)
            self.assertIn(vault / "03_Knowledge" / "hubs" / "AgentBus.md", created)
            graphify = (vault / "03_Knowledge" / "hubs" / "Graphify.md").read_text(encoding="utf-8")
            self.assertIn("[[Bucky]]", graphify)
            self.assertIn("[[JH System]]", graphify)

    def test_connect_isolated_notes_creates_indexes_linking_every_orphan(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "ObsidianVault"
            write_note(vault / "01_RAW" / "a.md", "raw note")
            write_note(vault / "09_Archive" / "b.md", "archive note")
            write_note(vault / "03_Knowledge" / "existing.md", "[[Bucky]]")

            result = kbb.connect_isolated_notes(vault, batch_size=1, dry_run=False)

            self.assertEqual(result["isolated"], 2)
            self.assertEqual(result["created"], 2)
            index_files = sorted((vault / "03_Knowledge" / "bridge-indexes").glob("*.md"))
            self.assertEqual(len(index_files), 2)
            merged = "\n".join(path.read_text(encoding="utf-8") for path in index_files)
            self.assertIn("[[01_RAW/a|a]]", merged)
            self.assertIn("[[09_Archive/b|b]]", merged)
            self.assertIn("[[JH System]]", merged)


if __name__ == "__main__":
    unittest.main()
