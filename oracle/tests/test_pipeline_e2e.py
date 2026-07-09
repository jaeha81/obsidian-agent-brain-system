#!/usr/bin/env python3
"""Phase 3 종단 파이프라인 검증 — Discord submit → 집PC claim → status → 조회.

①API ②Queue ③Registry ④Discord를 하나의 흐름으로 검증한다:
submit 측은 실제 client.py(submit_task/get_task)를, 집PC 폴링 측은 raw HTTP(/claim·/status)를
사용한다(실제 폴링 클라이언트는 별도 Phase). 로컬 api_server를 subprocess로 기동. 라이브 #2 미연결.

Usage:
    python -X utf8 oracle/tests/test_pipeline_e2e.py
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CORE = REPO / "oracle" / "core"
AGENTS_YAML = CORE / "agents.yaml"
TOKEN = "e2e-token-phase3"

sys.path.insert(0, str(CORE))
from client import submit_task, get_task  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="bucky_e2e_"))
with socket.socket() as _s:
    _s.bind(("127.0.0.1", 0))
    PORT = _s.getsockname()[1]
BASE = f"http://127.0.0.1:{PORT}"

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name} {detail}")


def homepc(method, path, body=None):
    """집PC 폴링 측 raw HTTP 호출. (status, json) 반환."""
    r = urllib.request.Request(BASE + path, method=method)
    r.add_header("Authorization", f"Bearer {TOKEN}")
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, data=data, timeout=10) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


env = dict(os.environ, BUCKY_API_TOKEN=TOKEN, BUCKY_DB_PATH=str(TMP / "e2e.db"),
           BUCKY_LOG_DIR=str(TMP / "logs"), BUCKY_AGENTS_FILE=str(AGENTS_YAML))
server = subprocess.Popen(
    [sys.executable, "-X", "utf8", str(CORE / "api_server.py"), "--host", "127.0.0.1",
     "--port", str(PORT)], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

print("== Phase 3 종단 파이프라인 (submit → claim → status → 조회) ==")
try:
    for _ in range(50):
        try:
            urllib.request.urlopen(BASE + "/health", timeout=2)
            break
        except OSError:
            time.sleep(0.2)

    # ① [Discord] high 우선 태스크 투입
    res = submit_task("research", payload={"instruction": "경쟁사 3곳 가격 조사"},
                      target_agent="home-pc-agent", priority="high",
                      source="discord", requested_by="jaeha#0001",
                      base_url=BASE, token=TOKEN)
    tid = res.get("task_id", "")
    check("E1 submit → pending + task_id",
          res.get("status") == "pending" and tid.startswith("task_"), f"got {res}")

    # ② [Discord] low 우선 태스크 하나 더 (정렬 확인용)
    res_low = submit_task("research", payload={"instruction": "저우선 잡"},
                          target_agent="home-pc-agent", priority="low",
                          base_url=BASE, token=TOKEN)
    check("E2 두 번째(low) pending", res_low.get("status") == "pending", f"got {res_low}")

    # ③ [집PC] home-pc-agent 폴링 — high 먼저 선점, payload 무결
    s, b = homepc("POST", "/api/v1/tasks/claim", {"agent_id": "home-pc-agent"})
    claimed = b.get("task") or {}
    check("E3 claim → high 선점 + assigned",
          s == 200 and claimed.get("task_id") == tid and claimed.get("status") == "assigned",
          f"got {s} {b}")
    check("E4 claim payload/target/priority 무결",
          claimed.get("payload") == {"instruction": "경쟁사 3곳 가격 조사"}
          and claimed.get("target_agent") == "home-pc-agent"
          and claimed.get("priority") == "high", f"got {claimed}")

    # ④ [집PC] 다른 에이전트는 home-pc 태스크 못 가져감(타깃 격리)
    s, b = homepc("POST", "/api/v1/tasks/claim", {"agent_id": "office-pc-agent"})
    check("E5 타깃 격리 → office-pc claim null", s == 200 and b.get("task") is None, f"got {s} {b}")

    # ⑤⑥ [집PC] 진행/완료 보고
    s, b = homepc("POST", f"/api/v1/tasks/{tid}/status", {"status": "running"})
    check("E6 assigned→running 200", s == 200 and b.get("status") == "running", f"got {s} {b}")
    s, b = homepc("POST", f"/api/v1/tasks/{tid}/status",
                  {"status": "completed", "result": {"found": 3, "avg_price": 51900}})
    check("E7 running→completed 200", s == 200 and b.get("status") == "completed", f"got {s} {b}")

    # ⑦ [Discord] 결과 조회 — 종단 왕복
    task = get_task(tid, base_url=BASE, token=TOKEN)
    check("E8 조회: completed + result·payload·메타 보존",
          task.get("status") == "completed"
          and task.get("result") == {"found": 3, "avg_price": 51900}
          and task.get("payload") == {"instruction": "경쟁사 3곳 가격 조사"}
          and task.get("source") == "discord"
          and task.get("requested_by") == "jaeha#0001", f"got {task}")

    # ⑧ [집PC] 큐 소진 — 완료분 제외, 저우선 1개만 남고 이후 null
    s, b = homepc("POST", "/api/v1/tasks/claim", {"agent_id": "home-pc-agent"})
    left = b.get("task") or {}
    check("E9 남은 저우선 태스크 선점",
          s == 200 and left.get("priority") == "low"
          and left.get("payload") == {"instruction": "저우선 잡"}, f"got {s} {b}")
    s, b = homepc("POST", "/api/v1/tasks/claim", {"agent_id": "home-pc-agent"})
    check("E10 큐 소진 → task:null", s == 200 and b.get("task") is None, f"got {s} {b}")
finally:
    server.kill()
    server.wait()

print(f"\n결과: {PASS} PASS / {FAIL} FAIL (총 {PASS + FAIL})")
sys.exit(1 if FAIL else 0)
