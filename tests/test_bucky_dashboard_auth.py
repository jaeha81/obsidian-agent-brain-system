import importlib
import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


class BuckyDashboardAuthTests(unittest.TestCase):
    def setUp(self):
        os.environ["BUCKY_DASH_PASSWORD"] = "test-password"
        sys.modules.pop("bucky_chat_server", None)
        self.server = importlib.import_module("bucky_chat_server")
        self.client = self.server.app.test_client()

    def test_dashboard_html_requires_auth_cookie(self):
        response = self.client.get("/index.html")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login.html", response.headers["Location"])

    def test_forged_local_cookie_is_rejected(self):
        self.client.set_cookie("bucky_auth", "local")
        response = self.client.get("/index.html")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login.html", response.headers["Location"])

    def test_login_sets_one_week_signed_cookie_and_hides_login_page(self):
        response = self.client.post("/api/login", data={"password": "test-password", "redirect": "/index.html"})
        self.assertEqual(response.status_code, 302)
        cookie = response.headers.get("Set-Cookie", "")
        self.assertIn("bucky_auth=", cookie)
        self.assertIn("Max-Age=604800", cookie)

        self.client.set_cookie("bucky_auth", self.server._auth_token())
        login = self.client.get("/login.html?r=/index.html")
        self.assertEqual(login.status_code, 302)
        self.assertEqual(login.headers["Location"], "/index.html")

    def test_trusted_source_does_not_login_without_password(self):
        response = self.client.post("/api/login", json={"password": "", "redirect": "/index.html"})
        self.assertEqual(response.status_code, 403)

    def test_launch_redirects_unauthenticated_user_to_login(self):
        response = self.client.get("/launch?next=/index.html")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login.html", response.headers["Location"])

    def test_login_page_does_not_attempt_blank_autologin(self):
        html = (ROOT / "docs" / "login.html").read_text(encoding="utf-8")
        self.assertNotIn("password: ''", html)
        self.assertNotIn("비밀번호 없이 자동 입장", html)

    def test_state_changing_api_requires_auth(self):
        response = self.client.post("/intake", json={"dashboard_type": "checklist"})
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
