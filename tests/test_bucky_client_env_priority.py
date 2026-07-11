"""bucky_client의 .env 로드 정책 테스트 — 호출측 env가 .env보다 우선(override=False).

provider_adapter.py(override=False)와 동일 정책인지 고정한다: bucky_client가
나중에 로드되어도 호출자·테스트가 명시한 환경변수를 덮어쓰지 않아야 한다.
"""

import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


class EnvPriorityTests(unittest.TestCase):
    def setUp(self):
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        sys.modules.pop("bucky_client", None)
        self.client = importlib.import_module("bucky_client")

    def test_caller_env_wins_over_dotenv(self):
        with tempfile.TemporaryDirectory() as td:
            envfile = Path(td) / ".env"
            envfile.write_text(
                "BUCKY_TEST_PRIORITY_KEY=dotenv-value\n"
                "BUCKY_TEST_FRESH_KEY=fresh-value\n",
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {"BUCKY_TEST_PRIORITY_KEY": "caller-value"}):
                os.environ.pop("BUCKY_TEST_FRESH_KEY", None)
                self.client._load_project_env(envfile)
                # 이미 설정된 키는 보존, 없던 키만 .env에서 채워진다
                self.assertEqual(os.environ["BUCKY_TEST_PRIORITY_KEY"], "caller-value")
                self.assertEqual(os.environ.get("BUCKY_TEST_FRESH_KEY"), "fresh-value")


if __name__ == "__main__":
    unittest.main()
