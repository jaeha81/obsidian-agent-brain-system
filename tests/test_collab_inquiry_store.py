import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TEST_TMP_ROOT = Path(r"C:\tmp")
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts import collab_inquiry_store as store  # noqa: E402


class TestCollabInquiryStore(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "name": "홍길동",
            "email": "hello@example.com",
            "company": "Example Studio",
            "summary": "AI agent dashboard build",
            "body": "Need proposal and development support.",
            "budget": "500",
            "timeline": "2026-Q3",
            "links": ["https://example.com/brief"],
        }

    def test_create_inquiry_writes_markdown_file(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            with mock.patch.object(store, "COLLAB_INBOX", Path(tmpdir)):
                path = store.create_inquiry(self.payload)
            text = path.read_text(encoding="utf-8")
        self.assertIn('type: "collab_inquiry"', text)
        self.assertIn('status: "new"', text)
        self.assertIn("Need proposal and development support.", text)

    def test_update_status_appends_activity_log(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            with mock.patch.object(store, "COLLAB_INBOX", Path(tmpdir)):
                path = store.create_inquiry(self.payload)
                store.update_status(path, "reviewing", actor="admin")
            text = path.read_text(encoding="utf-8")
        self.assertIn('status: "reviewing"', text)
        self.assertIn("admin changed status to reviewing", text)

    def test_save_admin_note_persists_note_section(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            with mock.patch.object(store, "COLLAB_INBOX", Path(tmpdir)):
                path = store.create_inquiry(self.payload)
                store.save_admin_note(path, "Need quick callback.")
            text = path.read_text(encoding="utf-8")
        self.assertIn("## Admin Notes", text)
        self.assertIn("Need quick callback.", text)


if __name__ == "__main__":
    unittest.main()
