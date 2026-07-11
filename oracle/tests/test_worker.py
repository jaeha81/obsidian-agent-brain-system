#!/usr/bin/env python3
"""Bucky Core 폴링 워커 검증 스위트 (Phase 3-⑤).

실서버(api_server.py)를 subprocess로 기동하고 worker.run_once를 in-process로 호출해
claim→running→completed(및 handle_task 예외→failed) 왕복을 검증한다.
test_client.py와 동일한 러너 스타일.

Usage:
    python -X utf8 oracle/tests/test_worker.py
"""
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

print(f"\n결과: {PASS} PASS / {FAIL} FAIL (총 {PASS + FAIL})")
sys.exit(1 if FAIL else 0)
