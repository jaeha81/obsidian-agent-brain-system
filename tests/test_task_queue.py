import importlib
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


class TaskQueueIdTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self.tmp.name) / "ObsidianVault"
        os.environ["VAULT_PATH"] = str(self.vault)
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        sys.modules.pop("task_queue", None)
        self.tq = importlib.import_module("task_queue")

    def tearDown(self):
        conn = getattr(self.tq, "_conn", None)
        if conn is not None:
            conn.close()
            self.tq._conn = None
        os.environ.pop("VAULT_PATH", None)
        self.tmp.cleanup()

    def test_add_uses_next_numeric_task_id_even_when_existing_task_is_not_today(self):
        db = self.tq.DB_PATH
        db.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS tasks ("
            "id TEXT PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL, "
            "agent TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', "
            "created TEXT NOT NULL, updated TEXT, result TEXT, source TEXT DEFAULT 'user')"
        )
        conn.execute(
            "INSERT INTO tasks (id,title,body,agent,status,created,source) VALUES (?,?,?,?,?,?,?)",
            ("T001", "old", "old", "bucky", "done", "2026-05-30T08:54:27", "test"),
        )
        conn.commit()
        conn.close()

        task = self.tq.add("new", "new body", "claude", source="test")

        self.assertEqual("T002", task["id"])


if __name__ == "__main__":
    unittest.main()
