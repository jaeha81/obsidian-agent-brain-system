#!/usr/bin/env python3
"""Bucky Core API Server 검증 스위트 (Phase 3-①②③).

stdlib만 사용. 로더 단위 테스트(in-process) + 실서버 HTTP 테스트(subprocess 기동).

Usage:
    python -X utf8 oracle/tests/test_api_server.py
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AGENTS_YAML = REPO / "oracle" / "core" / "agents.yaml"
TOKEN = "test-token-phase3"

sys.path.insert(0, str(REPO / "oracle" / "core"))
os.environ.setdefault("BUCKY_AGENTS_FILE", str(AGENTS_YAML))
import api_server  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="bucky_api_test_"))
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


def req(method: str, path: str, body: dict | None = None, auth: bool = True):
    """(status, json) 반환."""
    r = urllib.request.Request(BASE + path, method=method)
    if auth:
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


def load_from(name: str, yaml_text: str, encoding: str = "utf-8"):
    """임시 yaml로 load_agents 실행. 반환값 또는 SystemExit를 돌려준다."""
    f = TMP / name
    f.write_text(yaml_text, encoding=encoding)
    old = api_server.AGENTS_FILE
    api_server.AGENTS_FILE = f
    try:
        return api_server.load_agents()
    except SystemExit as e:
        return e
    finally:
        api_server.AGENTS_FILE = old


VALID_ONE = "agents:\n  - id: x\n    type: core\n    location: o\n    role: r\n    status: active\n"

print("== A. load_agents 단위 테스트 ==")
reg = api_server.load_agents()
check("A1 실파일 5개 로드", len(reg) == 5, f"got {len(reg)}")
check("A2 §21.2 id 일치", set(reg) == {
    "bucky-main", "home-pc-agent", "office-pc-agent", "laptop-agent", "interior-estimate-ai"})
check("A3 필드 값", reg["bucky-main"] == {
    "id": "bucky-main", "type": "core", "location": "oracle",
    "role": "central-brain", "status": "active"})
check("A4 status 값", reg["interior-estimate-ai"]["status"] == "development")

old = api_server.AGENTS_FILE
api_server.AGENTS_FILE = TMP / "no_such_agents.yaml"
try:
    api_server.load_agents()
    check("A5 파일 없음 → 기동 거부", False, "SystemExit 미발생")
except SystemExit:
    check("A5 파일 없음 → 기동 거부", True)
finally:
    api_server.AGENTS_FILE = old

check("A6 필수 필드 누락 → 거부",
      isinstance(load_from("a6.yaml", "agents:\n  - id: x\n    type: core\n"), SystemExit))
check("A7 id 중복 → 거부", isinstance(load_from(
    "a7.yaml",
    "agents:\n"
    + "  - id: dup\n    type: core\n    location: o\n    role: r\n    status: active\n" * 2,
), SystemExit))
check("A8 형식 오류 라인 → 거부",
      isinstance(load_from("a8.yaml", "agents:\n  - id: x\n    잘못된 라인\n"), SystemExit))
check("A9 빈 목록 → 거부", isinstance(load_from("a9.yaml", "agents:\n# 주석뿐\n"), SystemExit))
check("A10 agents: 헤더 없음 → 거부",
      isinstance(load_from("a10.yaml", "other:\n  - id: x\n"), SystemExit))

q = load_from("a11.yaml",
              'agents:\n  - id: "q-agent"  # 인라인 주석\n    type: local\n'
              "    location: 'home-pc'\n    role: r\n    status: active\n")
check("A11 따옴표 벗김·인라인 주석", not isinstance(q, SystemExit)
      and q["q-agent"]["location"] == "home-pc", f"got {q}")

# -- 리뷰 반영분 (BOM, 값 속 #, 키 중복) --
b = load_from("a12.yaml", VALID_ONE, encoding="utf-8-sig")
check("A12 UTF-8 BOM 파일 로드", not isinstance(b, SystemExit) and "x" in b, f"got {b}")
h = load_from("a13.yaml", VALID_ONE.replace("role: r", "role: back#end"))
check("A13 값 속 # 보존(공백 없는 #는 주석 아님)",
      not isinstance(h, SystemExit) and h["x"]["role"] == "back#end", f"got {h}")
check("A14 블록 내 키 중복 → 거부", isinstance(load_from(
    "a14.yaml", VALID_ONE + "    status: standby\n"), SystemExit))
check("A15 `- ` 누락 병합 → 거부(키 중복으로 검출)", isinstance(load_from(
    "a15.yaml", VALID_ONE + VALID_ONE.split("\n", 1)[1].replace("- id", "  id")), SystemExit))

print("== B. 실서버 HTTP 테스트 ==")
env = dict(
    os.environ,
    BUCKY_API_TOKEN=TOKEN,
    BUCKY_DB_PATH=str(TMP / "test_tasks.db"),
    BUCKY_LOG_DIR=str(TMP / "logs"),
    BUCKY_AGENTS_FILE=str(AGENTS_YAML),
)
server = subprocess.Popen(
    [sys.executable, "-X", "utf8", str(REPO / "oracle" / "core" / "api_server.py"),
     "--host", "127.0.0.1", "--port", str(PORT)],
    env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
)
try:
    for _ in range(50):
        try:
            if req("GET", "/health", auth=False) == (200, {"status": "ok"}):
                break
        except OSError:
            time.sleep(0.2)
    else:
        sys.exit("서버 기동 실패")
    check("B1 /health 무인증 200", True)

    # -- Agent Registry 엔드포인트 (③) --
    s, b = req("GET", "/api/v1/agents", auth=False)
    check("B2 /agents 무인증 401", s == 401, f"got {s}")
    s, b = req("GET", "/api/v1/agents")
    check("B3 /agents 200 + 5개", s == 200 and len(b["agents"]) == 5, f"got {s} {b}")
    check("B4 /agents 응답에 §21.2 id", {a["id"] for a in b["agents"]} == set(reg))
    s, b = req("GET", "/api/v1/agents/home-pc-agent")
    check("B5 /agents/{id} 200", s == 200 and b["role"] == "main-workstation", f"got {s} {b}")
    s, b = req("GET", "/api/v1/agents/ghost-agent")
    check("B6 미등록 id 404", s == 404, f"got {s}")
    s, b = req("GET", "/api/v1/agents/ghost-agent", auth=False)
    check("B7 /agents/{id} 무인증 401", s == 401, f"got {s}")

    # -- 태스크 생성 시 target_agent 검증 (③) --
    s, b = req("POST", "/api/v1/tasks", {"task_type": "echo"})
    check("B8 기본 target(bucky-main) 201", s == 201, f"got {s} {b}")
    s, b = req("POST", "/api/v1/tasks", {"task_type": "echo", "target_agent": "ghost-agent"})
    check("B9 미등록 target 400", s == 400 and "unknown target_agent" in b["error"], f"got {s} {b}")
    s, b = req("POST", "/api/v1/tasks",
               {"task_type": "echo", "target_agent": "home-pc-agent", "priority": "high",
                "payload": {"msg": "hi"}})
    check("B10 등록 target 201", s == 201, f"got {s} {b}")
    tid = b["task_id"]

    # -- 클레임 시 agent_id 검증 (③) --
    s, b = req("POST", "/api/v1/tasks/claim", {"agent_id": "ghost-agent"})
    check("B11 미등록 agent 클레임 400", s == 400 and "unknown agent_id" in b["error"], f"got {s} {b}")
    s, b = req("POST", "/api/v1/tasks/claim", {"agent_id": "home-pc-agent"})
    check("B12 등록 agent 클레임 200+assigned",
          s == 200 and b["task"]["task_id"] == tid and b["task"]["status"] == "assigned",
          f"got {s} {b}")
    s, b = req("POST", "/api/v1/tasks/claim", {"agent_id": "laptop-agent"})
    check("B13 빈 큐 클레임 task:null", s == 200 and b["task"] is None, f"got {s} {b}")

    # -- ①② 회귀: 상태 전이 + 조회 --
    s, b = req("POST", f"/api/v1/tasks/{tid}/status", {"status": "running"})
    check("B14 assigned→running 200", s == 200, f"got {s} {b}")
    s, b = req("POST", f"/api/v1/tasks/{tid}/status", {"status": "running"})
    check("B15 동일 상태 멱등 200", s == 200, f"got {s} {b}")
    s, b = req("POST", f"/api/v1/tasks/{tid}/status", {"status": "cancelled"})
    check("B16 전이표 밖 전이(running→cancelled) 409", s == 409, f"got {s} {b}")
    s, b = req("POST", f"/api/v1/tasks/{tid}/status",
               {"status": "completed", "result": {"ok": True}})
    check("B17 running→completed 200", s == 200, f"got {s} {b}")
    s, b = req("GET", f"/api/v1/tasks/{tid}")
    check("B18 조회: completed+result", s == 200 and b["status"] == "completed"
          and b["result"] == {"ok": True} and b["target_agent"] == "home-pc-agent",
          f"got {s} {b}")
    s, b = req("POST", "/api/v1/tasks", {"task_type": "echo", "priority": "urgent"})
    check("B19 잘못된 priority 400", s == 400, f"got {s}")
    s, b = req("POST", "/api/v1/tasks", {"task_type": "echo"}, auth=False)
    check("B20 태스크 생성 무인증 401", s == 401, f"got {s}")
    s, b = req("GET", "/api/v1/tasks/task_nope")
    check("B21 미존재 태스크 404", s == 404, f"got {s}")
    s, b = req("POST", "/api/v1/tasks", {"task_type": "echo", "target_agent": " bucky-main "})
    check("B22 패딩 target_agent trim 후 201", s == 201, f"got {s} {b}")

    # -- 동시 클레임 회귀 (10스레드, 태스크 5개 → 중복 0) --
    for i in range(5):
        req("POST", "/api/v1/tasks", {"task_type": f"cc{i}", "target_agent": "home-pc-agent"})
    got: list = []

    def claim():
        s, b = req("POST", "/api/v1/tasks/claim", {"agent_id": "home-pc-agent"})
        if b["task"]:
            got.append(b["task"]["task_id"])

    threads = [threading.Thread(target=claim) for _ in range(10)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    check("B23 동시 클레임 10스레드 중복 0", len(got) == 5 and len(set(got)) == 5,
          f"claimed {len(got)}, unique {len(set(got))}")
finally:
    server.kill()
    server.wait()

print(f"\n결과: {PASS} PASS / {FAIL} FAIL (총 {PASS + FAIL})")
sys.exit(1 if FAIL else 0)
