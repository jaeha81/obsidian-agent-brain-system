import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


class BuckySubAgentManagerChrisTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self.tmp.name) / "ObsidianVault"
        os.environ["VAULT_PATH"] = str(self.vault)
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        sys.modules.pop("bucky_sub_agent_manager", None)
        self.manager = importlib.import_module("bucky_sub_agent_manager")

    def tearDown(self):
        os.environ.pop("VAULT_PATH", None)
        self.tmp.cleanup()

    def test_graphify_knowledge_request_selects_chris(self):
        agent = self.manager.select_agent(
            "Graphify graph.json을 보고 지식 갭과 고립 노드 개선 후보를 정리해줘"
        )

        self.assertEqual("chris", agent)

    def test_delegate_creates_chris_inbox_task(self):
        result = self.manager.delegate("브레인 성능 관리를 위해 Graphify 연결성 리포트를 만들어줘")

        self.assertEqual("single", result["mode"])
        self.assertEqual("chris", result["tasks"][0]["agent"])
        self.assertTrue(Path(result["tasks"][0]["inbox_path"]).exists())
