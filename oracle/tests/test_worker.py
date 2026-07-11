#!/usr/bin/env python3
"""Bucky Core 폴링 워커 검증 스위트 (Phase 3-⑤).

실서버(api_server.py)를 subprocess로 기동하고 worker.run_once를 in-process로 호출해
claim→running→completed(및 handle_task 예외→failed) 왕복을 검증한다.
test_client.py와 동일한 러너 스타일.

Usage:
    python -X utf8 oracle/tests/test_worker.py
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CORE = REPO / "oracle" / "core"
AGENTS_YAML = CORE / "agents.yaml"
TOKEN = "test-token-worker"
AGENT = "home-pc-agent"

sys.path.insert(0, str(CORE))
import worker  # noqa: E402
from client import submit_task, get_task  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="bucky_worker_test_"))
with socket.socket() as _s:  # 빈 포트 확보 — 고정 포트 충돌 방지
    _s.bind(("127.0.0.1", 0))
    PORT = _s.getsockname()[1]
BASE = f"http://127.0.0.1:{PORT}"

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name} {detail}")


def _boom(task):  # handle_task 예외 경로 검증용
    raise RuntimeError("boom")


print("== 폴링 워커 테스트 (실서버) ==")
env = dict(
    os.environ,
    BUCKY_API_TOKEN=TOKEN,
    BUCKY_DB_PATH=str(TMP / "worker.db"),
    BUCKY_LOG_DIR=str(TMP / "logs"),
    BUCKY_AGENTS_FILE=str(AGENTS_YAML),
)
os.environ.pop("BUCKY_API_TOKEN", None)
os.environ.pop("ORACLE_API_URL", None)

server = subprocess.Popen(
    [sys.executable, "-X", "utf8", str(CORE / "api_server.py"),
     "--host", "127.0.0.1", "--port", str(PORT)],
    env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
)
try:
    for _ in range(50):
        try:
            urllib.request.urlopen(BASE + "/health", timeout=2)
            break
        except OSError:
            time.sleep(0.2)

    # W1 빈 큐 → run_once None
    check("W1 빈 큐 → run_once None",
          worker.run_once(AGENT, base_url=BASE, token=TOKEN) is None)

    # W2~W3 submit → run_once가 선점·실행·완료 보고 (result = AgentResult 규약, Stage 8)
    AGENT_RESULT_FIELDS = {"agent", "status", "summary", "files_changed",
                           "commands_run", "test_result", "risks", "next_actions"}
    res = submit_task("chat", payload={"instruction": "안녕"}, target_agent=AGENT,
                      base_url=BASE, token=TOKEN)
    tid = res["task_id"]
    done = worker.run_once(AGENT, base_url=BASE, token=TOKEN)
    check("W2 run_once가 해당 태스크 처리", done == tid, f"got {done}")
    task = get_task(tid, base_url=BASE, token=TOKEN)
    result = task.get("result") or {}
    check("W3 completed + AgentResult 형식 result (echo 보존)",
          task["status"] == "completed"
          and set(result) == AGENT_RESULT_FIELDS
          and result["agent"] == AGENT
          and result["status"] == "completed"
          and "안녕" in result["summary"],
          f"got {task}")

    # W4 타깃 격리 — office-pc-agent는 home-pc 태스크를 못 가져감
    submit_task("chat", payload={"x": 1}, target_agent=AGENT, base_url=BASE, token=TOKEN)
    check("W4 다른 에이전트 run_once → None",
          worker.run_once("office-pc-agent", base_url=BASE, token=TOKEN) is None)
    worker.run_once(AGENT, base_url=BASE, token=TOKEN)  # 청소: home-pc가 소진

    # W5~W6 handle_task 예외 → failed 보고 (워커는 죽지 않고 task_id 반환)
    res3 = submit_task("chat", payload={"boom": True}, target_agent=AGENT,
                       base_url=BASE, token=TOKEN)
    tid3 = res3["task_id"]
    orig = worker.handle_task
    worker.handle_task = _boom
    try:
        done3 = worker.run_once(AGENT, base_url=BASE, token=TOKEN)
    finally:
        worker.handle_task = orig
    check("W5 예외 태스크도 처리 후 task_id 반환", done3 == tid3, f"got {done3}")
    task3 = get_task(tid3, base_url=BASE, token=TOKEN)
    result3 = task3.get("result") or {}
    check("W6 handle_task 예외 → status failed + AgentResult(failed) 기록",
          task3["status"] == "failed"
          and result3.get("agent") == AGENT
          and result3.get("status") == "failed"
          and "boom" in result3.get("summary", ""),
          f"got {task3}")

    # W7 handle_task가 failed AgentResult를 반환하면 서버 상태도 failed로 보고
    res4 = submit_task("chat", payload={"instruction": "x"}, target_agent=AGENT,
                       base_url=BASE, token=TOKEN)
    tid4 = res4["task_id"]
    orig = worker.handle_task
    worker.handle_task = lambda task: worker.AgentResult(
        agent=AGENT, status="failed", summary="검증 실패 스텁").to_dict()
    try:
        done4 = worker.run_once(AGENT, base_url=BASE, token=TOKEN)
    finally:
        worker.handle_task = orig
    task4 = get_task(tid4, base_url=BASE, token=TOKEN)
    check("W7 failed AgentResult 반환 → 서버 status failed",
          done4 == tid4 and task4["status"] == "failed"
          and (task4.get("result") or {}).get("status") == "failed",
          f"got {task4}")
finally:
    server.kill()
    server.wait()

# W8~W10은 서버 불필요 — handle_task 계약을 직접 검증한다.
# W8 정본 병합 — payload가 큐 레코드의 task_id/task_type/priority를 덮어쓸 수 없다
r8 = worker.handle_task({
    "task_id": "task_20260711_120000_abcd", "task_type": "chat",
    "priority": "normal", "target_agent": AGENT,
    "payload": {"task_id": "evil", "task_type": "hack", "priority": "urgent",
                "instruction": "x"},
})
check("W8 큐 레코드 정본 필드가 payload를 이긴다",
      r8["status"] == "completed" and "echo(chat)" in r8["summary"], f"got {r8}")

# W9 invalid 레코드(task_id 형식 위반) → 예외 없이 AgentResult(failed)
r9 = worker.handle_task({"task_id": "not-oracle-format", "task_type": "chat",
                         "payload": {}})
check("W9 TaskSpec 검증 실패 → AgentResult(failed)",
      r9["status"] == "failed" and "TaskSpec" in r9["summary"], f"got {r9}")

# W10 클래스 정체성 — worker와 ProviderAdapter가 같은 core.task_spec.TaskSpec을 쓴다
import importlib  # noqa: E402
_canon = importlib.import_module("core.task_spec")
check("W10 worker.TaskSpec is core.task_spec.TaskSpec",
      worker.TaskSpec is _canon.TaskSpec)

# ── W11~W14 — Stage 17 어댑터 디스패치 (서버 불필요, 이벤트는 임시 경로로 격리) ──
# worker import가 scripts를 sys.path에 올린 뒤라 core.*/model_router/providers 접근 가능.
import model_router  # noqa: E402
import providers  # noqa: E402
from core import event_log  # noqa: E402
from core.provider_adapter import Estimate  # noqa: E402

# W11 리포 기본 config → 플래그 off (off일 때 echo 동작 자체는 W2~W3·W8이 회귀 보증)
check("W11 기본 features.worker_adapter_dispatch=false → 디스패치 비활성",
      worker._dispatch_enabled() is False)

DISPATCH_TASK = {
    "task_id": "task_20260712_090000_ab12", "task_type": "chat",
    "target_agent": AGENT, "payload": {"instruction": "hello"},
}


class _FakeAdapter:
    """estimate/run 계약만 흉내내는 스텁 — ok=False면 실행 불가 provider."""

    def __init__(self, name, ok=True):
        self.name, self._ok = name, ok

    def estimate(self, spec):
        return Estimate(self.name, self._ok, "sonnet" if self._ok else "",
                        "" if self._ok else "disabled 스텁")

    def run(self, spec, instruction=""):
        return worker.AgentResult(agent=self.name, status="completed",
                                  summary=f"adapter({self.name}): {instruction}")


def dispatch_case(chain, factory):
    """플래그 on + 가짜 체인/어댑터로 handle_task 실행 → (result, 기록된 이벤트 목록)."""
    tmp_log = Path(tempfile.mkdtemp(prefix="bucky_ev_")) / "events.jsonl"
    orig = (worker._dispatch_enabled, model_router.provider_candidates,
            providers.get_adapter, event_log.EVENTS_PATH)
    worker._dispatch_enabled = lambda: True
    model_router.provider_candidates = lambda task_type, policy=None: list(chain)
    providers.get_adapter = lambda name, registry=None: factory(name)
    event_log.EVENTS_PATH = tmp_log
    try:
        result = worker.handle_task(dict(DISPATCH_TASK))
    finally:
        (worker._dispatch_enabled, model_router.provider_candidates,
         providers.get_adapter, event_log.EVENTS_PATH) = orig
    events = []
    if tmp_log.is_file():
        events = [json.loads(ln) for ln in
                  tmp_log.read_text(encoding="utf-8").splitlines()]
    return result, events


# W12 on 디스패치 — 어댑터 결과 반환 + model_decision 이벤트(스키마 payload) 기록
r12, ev12 = dispatch_case(["fake_ok"], lambda name: _FakeAdapter(name))
md12 = [e for e in ev12 if e["kind"] == "model_decision"]
check("W12 플래그 on → 어댑터 결과 + model_decision 이벤트",
      r12["status"] == "completed" and r12["summary"] == "adapter(fake_ok): hello"
      and len(md12) == 1
      and md12[0]["task_id"] == DISPATCH_TASK["task_id"]
      and md12[0]["payload"]["selected_provider"] == "fake_ok"
      and md12[0]["payload"]["provider_chain"] == ["fake_ok"],
      f"got {r12} / events {ev12}")

# W13 disabled 폴백 — 1순위 실행 불가면 다음 provider가 실행
r13, ev13 = dispatch_case(["dead", "live"],
                          lambda name: _FakeAdapter(name, ok=(name == "live")))
check("W13 1순위 disabled → 2순위 폴백 실행",
      r13["status"] == "completed" and r13["summary"] == "adapter(live): hello",
      f"got {r13}")

# W14 전 provider 실행 불가 → 명시적 failed + worker_dispatch_failed 이벤트
r14, ev14 = dispatch_case(["dead"], lambda name: _FakeAdapter(name, ok=False))
df14 = [e for e in ev14 if e["kind"] == "worker_dispatch_failed"]
check("W14 실행 가능 provider 없음 → 명시적 failed + 이벤트",
      r14["status"] == "failed" and "디스패치 실패" in r14["summary"]
      and "dead" in r14["summary"]
      and len(df14) == 1 and df14[0]["payload"]["provider_chain"] == ["dead"]
      and df14[0]["payload"]["skipped"],
      f"got {r14} / events {ev14}")

print(f"\n결과: {PASS} PASS / {FAIL} FAIL (총 {PASS + FAIL})")
sys.exit(1 if FAIL else 0)
