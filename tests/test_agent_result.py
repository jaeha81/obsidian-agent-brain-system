"""scripts/core/agent_result.py 단위 테스트 — V3 Stage 4 AgentResult 계약.

왕복 직렬화 + oracle 큐 상태 체계 호환 크로스체크 + 스키마 계약 일치.
"""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from core.agent_result import VALID_STATUSES, AgentResult  # noqa: E402

SCHEMA = ROOT / "ObsidianVault" / "10_AgentBus" / "contracts" / "agent_result.schema.json"


def _load_oracle_api_server():
    oracle_core = ROOT / "oracle" / "core"
    if str(oracle_core) not in sys.path:
        sys.path.insert(0, str(oracle_core))
    try:
        import api_server  # noqa: PLC0415
        return api_server
    except Exception:
        return None


class RoundtripTests(unittest.TestCase):
    def test_minimal_roundtrip(self):
        res = AgentResult(agent="claude", status="completed")
        self.assertEqual(AgentResult.from_dict(res.to_dict()), res)

    def test_full_roundtrip(self):
        res = AgentResult(
            agent="claude",
            status="completed",
            summary="Stage 4 완료",
            files_changed=["scripts/core/task_spec.py"],
            commands_run=["python -m unittest tests.test_task_spec"],
            test_result="18 PASS",
            risks=["없음"],
            next_actions=["Stage 5 Codex 게이트"],
        )
        self.assertEqual(AgentResult.from_dict(res.to_dict()), res)

    def test_roundtrip_via_json(self):
        res = AgentResult(agent="codex", status="failed", risks=["회귀 우려"])
        restored = AgentResult.from_dict(json.loads(json.dumps(res.to_dict())))
        self.assertEqual(restored, res)

    def test_from_dict_ignores_unknown_keys(self):
        res = AgentResult(agent="claude", status="running")
        d = res.to_dict()
        d["updated_at"] = "2026-07-10"  # oracle record 여분 필드
        self.assertEqual(AgentResult.from_dict(d), res)


class ValidateTests(unittest.TestCase):
    def test_valid_result(self):
        self.assertEqual(AgentResult(agent="claude", status="completed").validate(), [])

    def test_all_valid_statuses_pass(self):
        for status in VALID_STATUSES:
            self.assertEqual(AgentResult(agent="a", status=status).validate(), [])

    def test_empty_agent(self):
        errors = AgentResult(agent="  ", status="completed").validate()
        self.assertTrue(any("agent" in e for e in errors))

    def test_bad_status(self):
        errors = AgentResult(agent="claude", status="done").validate()
        self.assertTrue(any("status" in e for e in errors))


class OracleCompatTests(unittest.TestCase):
    def test_statuses_match_oracle(self):
        api = _load_oracle_api_server()
        if api is None:
            self.skipTest("oracle api_server import 불가")
        oracle_statuses = set(api.TRANSITIONS.keys()) | set(api.STATUS_TARGETS)
        self.assertEqual(set(VALID_STATUSES), oracle_statuses)


class SchemaContractTests(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    def test_schema_is_valid_json(self):
        self.assertEqual(self.schema["title"], "AgentResult")

    def test_schema_properties_match_dataclass(self):
        res = AgentResult(agent="a", status="completed")
        self.assertEqual(set(self.schema["properties"]), set(res.to_dict()))

    def test_schema_status_enum_matches(self):
        self.assertEqual(tuple(self.schema["properties"]["status"]["enum"]), VALID_STATUSES)

    def test_schema_required_subset_of_properties(self):
        self.assertTrue(set(self.schema["required"]) <= set(self.schema["properties"]))


class ModelDecisionSchemaTests(unittest.TestCase):
    """model_decision.schema.json 구조 검증 (Python 클래스 없음 — 스키마 단독)."""

    def setUp(self):
        path = SCHEMA.parent / "model_decision.schema.json"
        self.schema = json.loads(path.read_text(encoding="utf-8"))

    def test_valid_json_and_title(self):
        self.assertEqual(self.schema["title"], "ModelDecision")

    def test_required_subset_of_properties(self):
        self.assertTrue(set(self.schema["required"]) <= set(self.schema["properties"]))

    def test_core_fields_present(self):
        for key in ("task_type", "selected_provider", "selected_model", "fallback_chain"):
            self.assertIn(key, self.schema["properties"])


if __name__ == "__main__":
    unittest.main()
