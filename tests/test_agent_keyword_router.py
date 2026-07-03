import importlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


class AgentKeywordRouterChrisTests(unittest.TestCase):
    def setUp(self):
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        sys.modules.pop("agent_keyword_router", None)
        self.router = importlib.import_module("agent_keyword_router")

    def test_graphify_knowledge_request_routes_to_chris(self):
        agent, hits = self.router.classify(
            "Graphify 기반으로 지식 정리하고 고립 노드와 브레인 성능 개선점을 찾아줘"
        )

        self.assertEqual("chris", agent)
        self.assertIn("graphify", [h.lower() for h in hits])

    def test_chris_hint_uses_chris_label(self):
        hint = self.router.format_routing_hint("chris", ["Graphify"])

        self.assertIn("CHRIS", hint)
        self.assertIn("Graphify", hint)


if __name__ == "__main__":
    unittest.main()
