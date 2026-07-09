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

    # W2~W3 submit → run_once가 선점·실행·완료 보고 (echo result 무결)
    res = submit_task("chat", payload={"instruction": "안녕"}, target_agent=AGENT,
                      base_url=BASE, token=TOKEN)
    tid = res["task_id"]
    done = worker.run_once(AGENT, base_url=BASE, token=TOKEN)
    check("W2 run_once가 해당 태스크 처리", done == tid, f"got {done}")
    task = get_task(tid, base_url=BASE, token=TOKEN)
    check("W3 completed + echo result 보존",
          task["status"] == "completed"
          and task["result"] == {"echo": {"instruction": "안녕"}, "handled_by": "worker-stub"},
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
    check("W6 handle_task 예외 → status failed + error 기록",
          task3["status"] == "failed" and "boom" in (task3.get("result") or {}).get("error", ""),
          f"got {task3}")
finally:
    server.kill()
    server.wait()

print(f"\n결과: {PASS} PASS / {FAIL} FAIL (총 {PASS + FAIL})")
sys.exit(1 if FAIL else 0)
