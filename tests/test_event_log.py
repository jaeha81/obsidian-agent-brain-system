"""scripts/core/event_log.py Stage 15 테스트 — envelope 고정 + 비차단 + model_decision 스키마 정합.

이벤트 로그는 단일 append-only 관측 로그(ADR-0003) — 버스·큐 아님.
emit()은 실패 시 None (예외 전파 금지). 실로그(05_Logs)는 건드리지 않고 tmp에만 기록.
"""

import json
import re
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from core.config import VAULT, load_routing_policy  # noqa: E402
from core.event_log import (  # noqa: E402
    ENVELOPE_KEYS,
    EVENTS_PATH,
    build_model_decision,
    emit,
    emit_model_decision,
)
from model_router import explain  # noqa: E402

SCHEMA_PATH = ROOT / "ObsidianVault" / "10_AgentBus" / "contracts" / "model_decision.schema.json"


class EmitEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.log = Path(self._tmp.name) / "events.jsonl"

    def test_envelope_keys_exact_order(self):
        p = emit("test_kind", task_id="t1", agent="a", model="sonnet", payload={"k": 1}, log_path=self.log)
        self.assertIsNotNone(p)
        e = json.loads(self.log.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(tuple(e.keys()), ENVELOPE_KEYS)

    def test_append_only_and_unique_event_ids(self):
        for _ in range(3):
            emit("test_kind", log_path=self.log)
        lines = self.log.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 3)
        ids = {json.loads(ln)["event_id"] for ln in lines}
        self.assertEqual(len(ids), 3)

    def test_ts_format(self):
        emit("test_kind", log_path=self.log)
        e = json.loads(self.log.read_text(encoding="utf-8").splitlines()[0])
        self.assertRegex(e["ts"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{4}$")

    def test_non_dict_payload_coerced_to_empty(self):
        emit("test_kind", payload="not-a-dict", log_path=self.log)  # type: ignore[arg-type]
        e = json.loads(self.log.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(e["payload"], {})

    def test_unserializable_payload_not_lost(self):
        p = emit("test_kind", payload={"path": Path("/x")}, log_path=self.log)
        self.assertIsNotNone(p)

    def test_failure_returns_none_without_raising(self):
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            blocked = Path(tf.name)
        self.addCleanup(blocked.unlink)
        self.assertIsNone(emit("x", log_path=blocked / "sub" / "e.jsonl"))

    def test_default_path_is_vault_05_logs(self):
        self.assertEqual(EVENTS_PATH, VAULT / "05_Logs" / "bucky-events.jsonl")


class BuildModelDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def _assert_schema_conformant(self, d: dict):
        for key in self.schema["required"]:
            self.assertIn(key, d)
        for key in d:  # additionalProperties: false
            self.assertIn(key, self.schema["properties"])
        self.assertGreaterEqual(len(d["task_type"]), 1)
        if "task_id" in d:
            self.assertRegex(d["task_id"], self.schema["properties"]["task_id"]["pattern"])
        self.assertRegex(d["decided_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_explain_output_conforms(self):
        d = build_model_decision(explain("review"), task_id="task_20260711_120000_ab12")
        self._assert_schema_conformant(d)
        self.assertEqual(d["selected_model"], "opus")

    def test_injected_provider_chain(self):
        d = build_model_decision(
            {"task_type": "code", "selected_model": "sonnet", "fallback_chain": ["sonnet", "haiku"]},
            provider_chain=["codex_pro", "claude_code"],
        )
        self._assert_schema_conformant(d)
        self.assertEqual(d["selected_provider"], "codex_pro")
        self.assertEqual(d["provider_chain"], ["codex_pro", "claude_code"])
        self.assertNotIn("task_id", d)

    def test_env_override_folded_into_reason(self):
        d = build_model_decision(
            {"task_type": "code", "selected_model": "opus", "reason": "r", "env_override": True},
            provider_chain=["claude_code"],
        )
        self.assertNotIn("env_override", d)
        self.assertIn("env_override", d["reason"])

    def test_selected_provider_matches_routing_policy(self):
        if not load_routing_policy():
            self.skipTest("routing_policy.yaml 로드 불가")
        d = build_model_decision(explain("review"))
        self.assertEqual(d["selected_provider"], "codex_pro")

    def test_malformed_explain_still_conforms(self):
        d = build_model_decision({}, provider_chain=["claude_code"])
        self._assert_schema_conformant(d)
        self.assertEqual(d["task_type"], "default")


class EmitModelDecisionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.log = Path(self._tmp.name) / "events.jsonl"

    def test_roundtrip_envelope_and_payload(self):
        p = emit_model_decision(
            explain("classify"),
            task_id="task_20260711_120000_ab12",
            agent="worker",
            provider_chain=["claude_code"],
            log_path=self.log,
        )
        self.assertIsNotNone(p)
        e = json.loads(self.log.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(e["kind"], "model_decision")
        self.assertEqual(e["model"], "haiku")
        self.assertEqual(e["payload"]["selected_model"], "haiku")
        self.assertEqual(e["payload"]["task_id"], "task_20260711_120000_ab12")

    def test_failure_returns_none(self):
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            blocked = Path(tf.name)
        self.addCleanup(blocked.unlink)
        self.assertIsNone(emit_model_decision(explain("code"), log_path=blocked / "sub" / "e.jsonl"))


if __name__ == "__main__":
    unittest.main()
