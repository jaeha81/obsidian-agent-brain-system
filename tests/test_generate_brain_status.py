"""scripts/generate_brain_status.py Stage 21 테스트 — 오라클 읽기전용 집계 + JSON 스키마.

강건성 원칙 검증이 핵심: DB/원장/로그/yaml 부재·손상 시에도 raise 없이 0/빈 값으로
degrade해야 한다 (build_system_evolution.py와 동일 원칙, G5 문서의 클린 clone 관례와 일치).
"""

import json
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import generate_brain_status as gbs  # noqa: E402


def _make_task_db(path: Path, rows: list[tuple[str, str]]) -> None:
    """(task_id, status) 목록으로 최소 tasks 테이블을 만든다 (api_server.py 스키마 부분집합)."""
    con = sqlite3.connect(path)
    try:
        con.execute("CREATE TABLE tasks (task_id TEXT PRIMARY KEY, status TEXT)")
        con.executemany("INSERT INTO tasks (task_id, status) VALUES (?, ?)", rows)
        con.commit()
    finally:
        con.close()


class TaskQueueSummaryTests(unittest.TestCase):
    def test_missing_db_degrades_to_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "no_such.db"
            result = gbs.task_queue_summary(missing)
        self.assertEqual(result["total"], 0)
        self.assertEqual(set(result["by_status"]), set(gbs.TASK_STATUSES))
        self.assertTrue(all(n == 0 for n in result["by_status"].values()))

    def test_counts_by_status_readonly(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "tasks.db"
            _make_task_db(db, [
                ("t1", "pending"), ("t2", "pending"), ("t3", "running"),
                ("t4", "completed"), ("t5", "unknown_status"),
            ])
            result = gbs.task_queue_summary(db)
        self.assertEqual(result["total"], 5)
        self.assertEqual(result["by_status"]["pending"], 2)
        self.assertEqual(result["by_status"]["running"], 1)
        self.assertEqual(result["by_status"]["completed"], 1)
        # 알려지지 않은 status 값도 total에는 포함되지만 by_status 고정 키에는 없다
        self.assertNotIn("unknown_status", result["by_status"])

    def test_readonly_connection_rejects_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "tasks.db"
            _make_task_db(db, [("t1", "pending")])
            con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
            try:
                with self.assertRaises(sqlite3.OperationalError):
                    con.execute("INSERT INTO tasks (task_id, status) VALUES ('x','pending')")
            finally:
                con.close()

    def test_corrupt_db_degrades_to_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            corrupt = Path(tmp) / "corrupt.db"
            corrupt.write_text("not a real sqlite file", encoding="utf-8")
            result = gbs.task_queue_summary(corrupt)
        self.assertEqual(result["total"], 0)


class UsageSummaryTests(unittest.TestCase):
    def test_missing_ledger_degrades_to_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = gbs.usage_summary(usage_dir=tmp, month="2020-01")
        self.assertEqual(result["records"], 0)
        self.assertEqual(result["cost_usd"], 0.0)
        self.assertEqual(result["by_model"], {})

    def test_aggregates_existing_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            month = "2026-07"
            path = Path(tmp) / f"{month}.jsonl"
            entry = {
                "ts": "2026-07-13T00:00:00+0900", "provider": "claude_code", "model": "sonnet",
                "layer": "cli", "task_id": "", "task_type": "", "source": "",
                "tokens_in": 100, "tokens_out": 200, "token_source": "reported",
                "cost_usd": 0.003, "duration_ms": None, "success": True,
            }
            path.write_text(json.dumps(entry) + "\n", encoding="utf-8")
            result = gbs.usage_summary(usage_dir=tmp, month=month)
        self.assertEqual(result["records"], 1)
        self.assertEqual(result["tokens_in"], 100)
        self.assertEqual(result["tokens_out"], 200)
        self.assertIn("claude_code/sonnet", result["by_model"])


class PolicyShadowSummaryTests(unittest.TestCase):
    def test_missing_log_degrades_to_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "no_events.jsonl"
            result = gbs.policy_shadow_summary(missing)
        self.assertEqual(result, {"total": 0, "by_tier": {}, "by_decision": {}, "budget_warnings": 0})

    def test_aggregates_policy_decision_and_budget_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            lines = [
                {"kind": "policy_decision", "payload": {"tier": "T0", "decision": "auto"}},
                {"kind": "policy_decision", "payload": {"tier": "T0", "decision": "auto"}},
                {"kind": "policy_decision", "payload": {"tier": "T3", "decision": "require_approval"}},
                {"kind": "budget_warning", "payload": {"cost_usd": 12.0}},
                {"kind": "model_decision", "payload": {}},  # 무관 kind — 무시돼야 함
                "not even json",  # 손상 라인 — 크래시 없이 스킵
            ]
            text = "\n".join(json.dumps(x) if not isinstance(x, str) else x for x in lines)
            path.write_text(text, encoding="utf-8")
            result = gbs.policy_shadow_summary(path)
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["by_tier"], {"T0": 2, "T3": 1})
        self.assertEqual(result["by_decision"], {"auto": 2, "require_approval": 1})
        self.assertEqual(result["budget_warnings"], 1)


class AgentsOrgTests(unittest.TestCase):
    def test_missing_file_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "agents.yaml"
            self.assertEqual(gbs.agents_org(missing), [])

    def test_parses_flat_agents_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "agents.yaml"
            path.write_text(
                "agents:\n"
                "  - id: node-a\n"
                "    type: local\n"
                "    location: home\n"
                "    role: worker\n"
                "    status: active\n"
                "  - id: node-b\n"
                "    status: standby\n",
                encoding="utf-8",
            )
            result = gbs.agents_org(path)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], {
            "id": "node-a", "type": "local", "location": "home",
            "role": "worker", "status": "active",
        })
        # 필드 결손은 crash 없이 빈 문자열로 (id만 있으면 유효 항목)
        self.assertEqual(result[1]["id"], "node-b")
        self.assertEqual(result[1]["type"], "")

    def test_real_agents_file_smoke(self):
        """실 oracle/core/agents.yaml — 5종 로드, 전부 id 보유 (test_registry.py 실등록부 스모크와 동일 취지)."""
        result = gbs.agents_org()
        self.assertTrue(result, "실 agents.yaml 로드 실패 — 5종이 있어야 함")
        self.assertTrue(all(a["id"] for a in result))

    def test_works_without_pyyaml(self):
        """07-13 실사고 회귀 방지: Task Scheduler 실행 환경(PyYAML 없음)에서 agents_org.json이
        조용히 빈 배열([])로 커밋된 사고가 있었다 — yaml import를 강제 차단해도 5종이
        전부 나와야 한다(PyYAML에 의존하지 않는 stdlib 평탄 파서를 쓴다는 증명).

        격리 subprocess에서 차단 후 모듈을 **처음부터** import한다 (G6 [P2], 07-14 이행).
        같은 프로세스 안에서 meta_path만 막으면 이미 import된 generate_brain_status를
        재사용하게 되어, 모듈 최상위에 PyYAML 의존성이 재도입되는 회귀를 놓친다.
        """
        code = textwrap.dedent(f"""
            import json, sys
            import importlib.abc

            class _BlockYaml(importlib.abc.MetaPathFinder):
                def find_spec(self, name, path, target=None):
                    if name == "yaml" or name.startswith("yaml."):
                        raise ImportError("시뮬레이션: PyYAML 없음 (Task Scheduler 환경 재현)")
                    return None

            sys.meta_path.insert(0, _BlockYaml())

            # 차단기가 실제로 살아있는지 먼저 증명한다 — 이게 없으면 PyYAML이 그냥 설치돼
            # 있기만 해도 이 테스트가 공허하게 통과한다.
            try:
                import yaml
                sys.exit("BLOCKER_DEAD: yaml이 차단되지 않았다")
            except ImportError:
                pass

            sys.path.insert(0, {str(SCRIPTS)!r})
            import generate_brain_status as gbs  # 최초 import — 최상위 yaml 의존이면 여기서 죽는다

            print(json.dumps([a["id"] for a in gbs.agents_org()]))
        """)
        proc = subprocess.run([sys.executable, "-X", "utf8", "-c", code],
                              capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0,
                         f"PyYAML 부재 환경에서 실패:\nstdout={proc.stdout}\nstderr={proc.stderr}")
        ids = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(len(ids), 5, f"PyYAML 차단 상태에서 5종이 아님: {ids}")
        self.assertTrue(all(ids))


class BuildAndMainIntegrationTests(unittest.TestCase):
    def test_main_writes_valid_json_schema(self):
        """main()을 실제 경로 그대로 실행 — 존재하는 실 데이터 기준 스키마만 검증(내용 값은 불문)."""
        with tempfile.TemporaryDirectory() as tmp:
            out_status = Path(tmp) / "bucky_brain_status.json"
            out_agents = Path(tmp) / "agents_org.json"
            orig = (gbs.OUT_STATUS, gbs.OUT_AGENTS)
            gbs.OUT_STATUS, gbs.OUT_AGENTS = out_status, out_agents
            try:
                rc = gbs.main()
            finally:
                gbs.OUT_STATUS, gbs.OUT_AGENTS = orig

            self.assertEqual(rc, 0)
            status = json.loads(out_status.read_text(encoding="utf-8"))
            self.assertEqual(set(status.keys()), {"meta", "task_queue", "usage", "policy_shadow"})
            self.assertIn("last_updated", status["meta"])
            self.assertEqual(set(status["task_queue"].keys()), {"total", "by_status"})
            self.assertEqual(set(status["usage"].keys()),
                              {"month", "records", "tokens_in", "tokens_out", "cost_usd", "by_model"})
            self.assertEqual(set(status["policy_shadow"].keys()),
                              {"total", "by_tier", "by_decision", "budget_warnings"})

            org = json.loads(out_agents.read_text(encoding="utf-8"))
            self.assertEqual(set(org.keys()), {"meta", "agents"})
            self.assertIsInstance(org["agents"], list)


if __name__ == "__main__":
    unittest.main()
