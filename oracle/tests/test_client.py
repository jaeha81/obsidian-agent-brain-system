#!/usr/bin/env python3
"""Bucky Core API 클라이언트 검증 스위트 (Phase 3-④).

stdlib만 사용. 실서버(api_server.py)를 subprocess로 기동하고 client.submit_task/get_task를
in-process로 호출해 왕복·오류 경로를 검증한다. test_api_server.py와 동일한 러너 스타일.

Usage:
    python -X utf8 oracle/tests/test_client.py
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CORE = REPO / "oracle" / "core"
AGENTS_YAML = CORE / "agents.yaml"
TOKEN = "test-token-phase3-client"

sys.path.insert(0, str(CORE))
import client  # noqa: E402
from client import (  # noqa: E402
    OracleClientError,
    submit_task,
    get_task,
    claim_task,
    update_status,
    index_search,
    index_stats,
)

TMP = Path(tempfile.mkdtemp(prefix="bucky_client_test_"))
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


def raises(fn, status=None):
    """fn() 호출이 OracleClientError를 던지면 (True, err) — status 일치까지 확인."""
    try:
        fn()
        return False, None
    except OracleClientError as e:
        if status is not None and e.status != status:
            return False, e
        return True, e
    except Exception as e:  # 다른 예외는 실패
        return False, e


print("== 클라이언트 통합 테스트 (실서버) ==")
INDEX_DIR = TMP / "index"  # 서버 기동 시점엔 미구축 — C16/C17이 빈 상태를 먼저 검증
env = dict(
    os.environ,
    BUCKY_API_TOKEN=TOKEN,
    BUCKY_DB_PATH=str(TMP / "test_tasks.db"),
    BUCKY_LOG_DIR=str(TMP / "logs"),
    BUCKY_AGENTS_FILE=str(AGENTS_YAML),
    OBSIDIAN_INDEX_DIR=str(INDEX_DIR),
)
# 클라이언트가 실수로 env를 읽어 통과하는 위양성을 막기 위해, 명시 인자 테스트 구간에서는
# 프로세스 env에서 토큰/URL을 비워 둔다(서버 subprocess는 위 env 사본으로 별도 기동).
os.environ.pop("BUCKY_API_TOKEN", None)
os.environ.pop("ORACLE_API_URL", None)

server = subprocess.Popen(
    [sys.executable, "-X", "utf8", str(CORE / "api_server.py"),
     "--host", "127.0.0.1", "--port", str(PORT)],
    env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
)
try:
    # 기동 대기 — get_task 404가 뜨면 서버가 응답 중이라는 신호
    ready = False
    for _ in range(50):
        ok, _e = raises(lambda: get_task("task_nope", base_url=BASE, token=TOKEN), status=404)
        if ok:
            ready = True
            break
        time.sleep(0.2)
    check("C0 서버 기동", ready)

    # C1~C2 submit → get 왕복
    res = submit_task(
        "chat",
        payload={"instruction": "안녕 버키"},
        target_agent="bucky-main",
        priority="high",
        source="discord",
        requested_by="tester",
        base_url=BASE,
        token=TOKEN,
    )
    check("C1 submit 성공 task_id+pending",
          res.get("status") == "pending" and res.get("task_id", "").startswith("task_"),
          f"got {res}")
    tid = res["task_id"]
    task = get_task(tid, base_url=BASE, token=TOKEN)
    check("C2 get 왕복: payload·target·priority 보존",
          task["status"] == "pending"
          and task["payload"] == {"instruction": "안녕 버키"}
          and task["target_agent"] == "bucky-main"
          and task["priority"] == "high"
          and task["source"] == "discord"
          and task["requested_by"] == "tester",
          f"got {task}")

    # C3 미등록 에이전트 → 400
    ok, e = raises(
        lambda: submit_task("chat", target_agent="ghost-agent", base_url=BASE, token=TOKEN),
        status=400,
    )
    check("C3 미등록 target_agent 400", ok, f"got {e!r}")

    # C4 잘못된 토큰 → 401
    ok, e = raises(
        lambda: submit_task("chat", base_url=BASE, token="wrong-token"),
        status=401,
    )
    check("C4 잘못된 토큰 401", ok, f"got {e!r}")

    # C5 task_type 누락(빈 값) → 서버 400
    ok, e = raises(
        lambda: submit_task("", base_url=BASE, token=TOKEN),
        status=400,
    )
    check("C5 빈 task_type 400", ok, f"got {e!r}")

    # C6 미존재 태스크 조회 → 404
    ok, e = raises(
        lambda: get_task("task_does_not_exist", base_url=BASE, token=TOKEN),
        status=404,
    )
    check("C6 미존재 태스크 404", ok, f"got {e!r}")

    # C7 env 기반 설정(ORACLE_API_URL + BUCKY_API_TOKEN)으로도 동작
    os.environ["ORACLE_API_URL"] = BASE
    os.environ["BUCKY_API_TOKEN"] = TOKEN
    try:
        res2 = submit_task("chat", payload={"instruction": "env 경유"})
        check("C7 env 설정 경유 submit 성공", res2.get("status") == "pending", f"got {res2}")
    finally:
        os.environ.pop("ORACLE_API_URL", None)
        os.environ.pop("BUCKY_API_TOKEN", None)

    # C8 토큰 미설정 → 네트워크 이전에 OracleClientError(status None)
    ok, e = raises(lambda: submit_task("chat", base_url=BASE, token=None))
    check("C8 토큰 없음 → 호출 전 예외(status None)",
          ok and e is not None and e.status is None, f"got {ok} {e!r}")

    # --- 폴링 측(claim_task/update_status) ---
    # C9 submit → claim으로 선점(→assigned)
    sub = submit_task("chat", payload={"instruction": "폴링용"}, target_agent="home-pc-agent",
                      base_url=BASE, token=TOKEN)
    claimed = claim_task("home-pc-agent", base_url=BASE, token=TOKEN)
    check("C9 claim → 해당 태스크 + assigned",
          claimed is not None and claimed["task_id"] == sub["task_id"]
          and claimed["status"] == "assigned", f"got {claimed}")

    # C10~C11 running → completed 전이 + result 첨부
    up = update_status(sub["task_id"], "running", base_url=BASE, token=TOKEN)
    check("C10 assigned→running", up.get("status") == "running", f"got {up}")
    up2 = update_status(sub["task_id"], "completed", result={"reply": "됐어"},
                        base_url=BASE, token=TOKEN)
    check("C11 running→completed", up2.get("status") == "completed", f"got {up2}")
    done = get_task(sub["task_id"], base_url=BASE, token=TOKEN)
    check("C12 result 보존", done.get("result") == {"reply": "됐어"}, f"got {done}")

    # C13 큐 소진 → claim None
    check("C13 빈 큐 claim → None",
          claim_task("home-pc-agent", base_url=BASE, token=TOKEN) is None)

    # C14 미등록 agent_id → 서버 400
    ok, e = raises(lambda: claim_task("ghost-agent", base_url=BASE, token=TOKEN), status=400)
    check("C14 미등록 agent_id claim 400", ok, f"got {e!r}")

    # C15 허용되지 않는 전이(completed→running) → 서버 409
    ok, e = raises(
        lambda: update_status(sub["task_id"], "running", base_url=BASE, token=TOKEN),
        status=409,
    )
    check("C15 잘못된 전이 409", ok, f"got {e!r}")

    # --- obsidian-index 측(index_search/index_stats, B4 #1) ---
    # C16 인덱스 미구축: stats는 200 + available=False
    st = index_stats(base_url=BASE, token=TOKEN)
    check("C16 인덱스 없음 → stats available=False",
          st.get("available") is False and st.get("count") == 0, f"got {st}")

    # C17 인덱스 미구축 검색 → 503
    ok, e = raises(lambda: index_search("버키", base_url=BASE, token=TOKEN), status=503)
    check("C17 인덱스 없음 검색 503", ok, f"got {e!r}")

    # C18 인덱스 생성(mtime 캐시가 재기동 없이 반영) 후 검색 — 지식 선반이 원본 선반보다 상위
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    recs = [
        {"slug": "bucky-core", "path": "03_Knowledge/bucky-core.md", "title": "버키 코어 설계",
         "folder": "03_Knowledge", "type": "knowledge", "keywords": ["버키", "코어"],
         "headings": ["설계"], "tags": ["core"], "snippet": "버키 코어 설계 노트"},
        {"slug": "bucky-raw", "path": "01_RAW/bucky-raw.md", "title": "버키 원본 메모",
         "folder": "01_RAW", "type": "raw", "keywords": ["버키"],
         "headings": [], "tags": [], "snippet": "원본 메모"},
    ]
    (INDEX_DIR / "records.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in recs), encoding="utf-8")
    (INDEX_DIR / "manifest.json").write_text(
        json.dumps({"count": 2, "schema_version": 1,
                    "generated_at": "2026-07-10T00:00:00",
                    "folders": {"03_Knowledge": 1, "01_RAW": 1}}, ensure_ascii=False),
        encoding="utf-8")
    hits = index_search("버키", base_url=BASE, token=TOKEN)
    check("C18 검색 성공 + 지식 선반 상위",
          hits.get("count") == 2 and hits["results"][0]["folder"] == "03_Knowledge",
          f"got {hits}")

    # C19 folder 필터 — 해당 선반만 반환
    hits2 = index_search("버키", folder="01_RAW", base_url=BASE, token=TOKEN)
    check("C19 folder 필터",
          hits2.get("count") == 1 and hits2["results"][0]["slug"] == "bucky-raw",
          f"got {hits2}")

    # C20 stats가 생성된 인덱스를 반영
    st2 = index_stats(base_url=BASE, token=TOKEN)
    check("C20 stats available=True count=2",
          st2.get("available") is True and st2.get("count") == 2, f"got {st2}")

    # C21 빈 질의 → 서버 400
    ok, e = raises(lambda: index_search("  ", base_url=BASE, token=TOKEN), status=400)
    check("C21 빈 질의 400", ok, f"got {e!r}")
finally:
    server.kill()
    server.wait()

print(f"\n결과: {PASS} PASS / {FAIL} FAIL (총 {PASS + FAIL})")
sys.exit(1 if FAIL else 0)
