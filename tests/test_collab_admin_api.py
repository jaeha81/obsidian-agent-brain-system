import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


class CollabAdminApiTests(unittest.TestCase):
    def setUp(self):
        os.environ["BUCKY_DASH_PASSWORD"] = "test-password"
        sys.modules.pop("bucky_chat_server", None)
        self.server = importlib.import_module("bucky_chat_server")
        self.client = self.server.app.test_client()

    def test_public_collab_inquiry_submission_is_allowed(self):
        with tempfile.TemporaryDirectory(dir=r"C:\tmp") as tmpdir:
            with mock.patch.object(self.server.collab_inquiry_store, "COLLAB_INBOX", Path(tmpdir)):
                response = self.client.post(
                    "/collab/inquiries",
                    json={
                        "requester_name": "홍길동",
                        "requester_email": "hello@example.com",
                        "summary": "AI dashboard build",
                        "body": "Need proposal and implementation.",
                    },
                )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["status"], "created")

    def test_collab_inquiry_list_requires_auth(self):
        response = self.client.get("/collab/inquiries")
        self.assertEqual(response.status_code, 401)

    def test_authenticated_collab_inquiry_list_returns_saved_items(self):
        with tempfile.TemporaryDirectory(dir=r"C:\tmp") as tmpdir:
            inbox = Path(tmpdir)
            with mock.patch.object(self.server.collab_inquiry_store, "COLLAB_INBOX", inbox):
                self.server.collab_inquiry_store.create_inquiry(
                    {
                        "requester_name": "홍길동",
                        "requester_email": "hello@example.com",
                        "summary": "AI dashboard build",
                        "body": "Need proposal and implementation.",
                    }
                )
                response = self.client.get("/collab/inquiries", headers={"X-Collab-Admin-Password": "ljh911314"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["summary"], "AI dashboard build")

    def test_authenticated_collab_note_and_status_updates_persist(self):
        with tempfile.TemporaryDirectory(dir=r"C:\tmp") as tmpdir:
            inbox = Path(tmpdir)
            with mock.patch.object(self.server.collab_inquiry_store, "COLLAB_INBOX", inbox):
                path = self.server.collab_inquiry_store.create_inquiry(
                    {
                        "requester_name": "홍길동",
                        "requester_email": "hello@example.com",
                        "summary": "AI dashboard build",
                        "body": "Need proposal and implementation.",
                    }
                )
                request_id = self.server.collab_inquiry_store.load_inquiry(path)["request_id"]
                headers = {"X-Collab-Admin-Password": "ljh911314"}
                note_response = self.client.post(f"/collab/inquiries/{request_id}/note", json={"note": "Need quick callback."}, headers=headers)
                status_response = self.client.post(f"/collab/inquiries/{request_id}/status", json={"status": "reviewing"}, headers=headers)
                record = self.server.collab_inquiry_store.load_inquiry(path)
        self.assertEqual(note_response.status_code, 200)
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(record["status"], "reviewing")
        self.assertEqual(record["admin_notes"], "Need quick callback.")

    def test_collab_discord_dispatch_endpoint_enqueues_payload(self):
        with tempfile.TemporaryDirectory(dir=r"C:\tmp") as tmpdir:
            inbox = Path(tmpdir) / "collab_inbox"
            queue_dir = Path(tmpdir) / "queue"
            with mock.patch.object(self.server.collab_inquiry_store, "COLLAB_INBOX", inbox):
                with mock.patch.object(self.server, "INTAKE_QUEUE_DIR", queue_dir):
                    path = self.server.collab_inquiry_store.create_inquiry(
                        {
                            "requester_name": "Hong",
                            "requester_email": "hello@example.com",
                            "summary": "AI dashboard build",
                            "body": "Need proposal and implementation.",
                        }
                    )
                    request_id = self.server.collab_inquiry_store.load_inquiry(path)["request_id"]
                    response = self.client.post(
                        f"/collab/inquiries/{request_id}/discord-dispatch",
                        headers={"X-Collab-Admin-Password": "ljh911314"},
                    )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.get_json()["status"], "accepted")


if __name__ == "__main__":
    unittest.main()
