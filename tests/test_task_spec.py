"""scripts/core/task_spec.py 단위 테스트 — V3 Stage 4 TaskSpec 계약.

왕복 직렬화 + oracle 큐 호환(task_id·priority) 크로스체크 + 스키마 계약 일치.
"""

import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from core.task_spec import PRIORITIES, TASK_ID_RE, TaskSpec, new_task_id  # noqa: E402

SCHEMA = ROOT / "ObsidianVault" / "10_AgentBus" / "contracts" / "task_spec.schema.json"


def _load_oracle_api_server():
    """oracle/core/api_server.py를 import. 의존성 부재 시 None."""
    oracle_core = ROOT / "oracle" / "core"
    if str(oracle_core) not in sys.path:
        sys.path.insert(0, str(oracle_core))
    try:
        import api_server  # noqa: PLC0415
        return api_server
    except Exception:
        return None


class TaskIdTests(unittest.TestCase):
    def test_new_task_id_matches_oracle_format(self):
        tid = new_task_id(datetime(2026, 7, 10, 14, 30, 22, tzinfo=timezone.utc))
        self.assertTrue(TASK_ID_RE.match(tid), tid)
        self.assertTrue(tid.startswith("task_20260710_143022_"))

    def test_new_task_id_unique(self):
        self.assertNotEqual(new_task_id(), new_task_id())


class RoundtripTests(unittest.TestCase):
    def test_minimal_roundtrip(self):
        spec = TaskSpec(task_id=new_task_id(), task_type="code")
        self.assertEqual(TaskSpec.from_dict(spec.to_dict()), spec)

    def test_full_roundtrip(self):
        spec = TaskSpec(
            task_id=new_task_id(),
            task_type="review",
            source="discord",
            channel="bucky-upgrade",
            priority="high",
            required_capabilities=["python", "security"],
            constraints={"no_commit": True},
            expected_output="리뷰 보고서",
        )
        self.assertEqual(TaskSpec.from_dict(spec.to_dict()), spec)

    def test_roundtrip_via_json(self):
        spec = TaskSpec(task_id=new_task_id(), task_type="code", constraints={"k": "v"})
        restored = TaskSpec.from_dict(json.loads(json.dumps(spec.to_dict())))
        self.assertEqual(restored, spec)

    def test_from_dict_ignores_unknown_keys(self):
        spec = TaskSpec(task_id=new_task_id(), task_type="code")
        d = spec.to_dict()
        d["target_agent"] = "bucky-main"  # oracle record 여분 필드
        d["status"] = "pending"
        self.assertEqual(TaskSpec.from_dict(d), spec)


class ValidateTests(unittest.TestCase):
    def test_valid_spec(self):
        self.assertEqual(TaskSpec(task_id=new_task_id(), task_type="code").validate(), [])

    def test_bad_task_id(self):
        errors = TaskSpec(task_id="nope", task_type="code").validate()
        self.assertTrue(any("task_id" in e for e in errors))

    def test_empty_task_type(self):
        errors = TaskSpec(task_id=new_task_id(), task_type="  ").validate()
        self.assertTrue(any("task_type" in e for e in errors))

    def test_bad_priority(self):
        errors = TaskSpec(task_id=new_task_id(), task_type="code", priority="urgent").validate()
        self.assertTrue(any("priority" in e for e in errors))

    def test_created_at_autofilled(self):
        self.assertTrue(TaskSpec(task_id=new_task_id(), task_type="code").created_at)


class InvalidInputTests(unittest.TestCase):
    """비정상 타입 입력 — 검증 경계에서 예외 없이 오류 목록으로 보고 (Codex 필수 수정 2)."""

    def test_non_string_fields_report_errors(self):
        errors = TaskSpec(task_id=123, task_type=456).validate()
        self.assertTrue(any("task_id" in e for e in errors))
        self.assertTrue(any("task_type" in e for e in errors))

    def test_none_fields_report_errors(self):
        errors = TaskSpec(task_id=None, task_type=None).validate()
        self.assertTrue(any("task_id" in e for e in errors))
        self.assertTrue(any("task_type" in e for e in errors))

    def test_from_dict_none_returns_invalid_spec(self):
        spec = TaskSpec.from_dict(None)
        self.assertIsInstance(spec, TaskSpec)
        self.assertTrue(spec.validate())

    def test_from_dict_non_dict_returns_invalid_spec(self):
        for bad in ("문자열", 42, ["list"]):
            self.assertTrue(TaskSpec.from_dict(bad).validate(), repr(bad))


class OracleCompatTests(unittest.TestCase):
    def test_priorities_match_oracle(self):
        api = _load_oracle_api_server()
        if api is None:
            self.skipTest("oracle api_server import 불가")
        self.assertEqual(PRIORITIES, api.PRIORITIES)

    def test_task_id_regex_matches_oracle_generator(self):
        api = _load_oracle_api_server()
        if api is None:
            self.skipTest("oracle api_server import 불가")
        oracle_id = api.new_task_id(datetime(2026, 7, 10, 1, 2, 3, tzinfo=timezone.utc))
        self.assertTrue(TASK_ID_RE.match(oracle_id), oracle_id)


class SchemaContractTests(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    def test_schema_is_valid_json(self):
        self.assertEqual(self.schema["title"], "TaskSpec")

    def test_schema_properties_match_dataclass(self):
        spec = TaskSpec(task_id=new_task_id(), task_type="code")
        self.assertEqual(set(self.schema["properties"]), set(spec.to_dict()))

    def test_schema_priority_enum_matches(self):
        self.assertEqual(tuple(self.schema["properties"]["priority"]["enum"]), PRIORITIES)

    def test_schema_required_subset_of_properties(self):
        self.assertTrue(set(self.schema["required"]) <= set(self.schema["properties"]))


if __name__ == "__main__":
    unittest.main()
