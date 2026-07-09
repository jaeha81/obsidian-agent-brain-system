#!/usr/bin/env python3
"""Bucky Core API Server — Oracle #2 (Phase 3-①+②+③).

명령 수신 최소형: 태스크 생성/조회 + Bearer 토큰 인증. stdlib만 사용해 #2(aarch64)에서
pip 설치 없이 기동한다. Phase 3-② Task Queue: 집PC가 /claim으로 폴링(pull)해 태스크를
가져가고 /status로 진행·결과를 보고한다. Phase 3-③ Agent Registry: 정적 YAML(§21.2)을
기동 시 로드해 에이전트 조회 API를 제공하고, 태스크 생성·클레임의 에이전트 ID를 검증한다.

Usage:
    BUCKY_API_TOKEN=<token> python3 oracle/core/api_server.py [--host 127.0.0.1] [--port 8700]

Endpoints:
    GET  /health                       → {"status": "ok"}             (인증 불필요 — 모니터링용)
    POST /api/v1/tasks                 → 201 {"task_id", "status"}    (Bearer)
    GET  /api/v1/tasks/{task_id}       → 200 task record | 404        (Bearer)
    POST /api/v1/tasks/claim           → 200 {"task": record|null}    (Bearer) 집PC 폴링 클레임
    POST /api/v1/tasks/{task_id}/status → 200 {"task_id", "status"}   (Bearer) §20.2 상태 전이
    GET  /api/v1/agents                → 200 {"agents": [...]}        (Bearer) 레지스트리 전체
    GET  /api/v1/agents/{agent_id}     → 200 agent record | 404       (Bearer)

Env:
    BUCKY_API_TOKEN        인증 토큰. 없으면 BUCKY_API_TOKEN_FILE에서 읽고, 둘 다 없으면 기동 거부.
    BUCKY_API_TOKEN_FILE   토큰 파일 경로 (기본 /etc/ai-os/bucky_api_token)
    BUCKY_DB_PATH          SQLite 경로 (기본 <repo>/data/bucky_tasks.db)
    BUCKY_LOG_DIR          JSONL 로그 디렉터리 (기본 <repo>/logs/api)
    BUCKY_AGENTS_FILE      Agent Registry YAML 경로 (기본 <repo>/oracle/core/agents.yaml)
"""

from __future__ import annotations

import argparse
import hmac
import json
import os
import re
import secrets
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.environ.get("BUCKY_DB_PATH", ROOT / "data" / "bucky_tasks.db"))
LOG_DIR = Path(os.environ.get("BUCKY_LOG_DIR", ROOT / "logs" / "api"))
TOKEN_FILE = Path(os.environ.get("BUCKY_API_TOKEN_FILE", "/etc/ai-os/bucky_api_token"))
AGENTS_FILE = Path(os.environ.get("BUCKY_AGENTS_FILE", ROOT / "oracle" / "core" / "agents.yaml"))

MAX_BODY_BYTES = 1 * 1024 * 1024
PRIORITIES = ("low", "normal", "high")
# §20.2 상태 전이 허용표. pending→assigned는 /claim 전용이라 여기에 없다.
TRANSITIONS = {
    "pending": {"cancelled"},
    "assigned": {"running", "failed", "cancelled"},
    "running": {"waiting", "completed", "failed"},
    "waiting": {"running", "completed", "failed", "cancelled"},
}
STATUS_TARGETS = frozenset().union(*TRANSITIONS.values())


def load_token() -> str:
    token = os.environ.get("BUCKY_API_TOKEN", "").strip()
    if not token and TOKEN_FILE.is_file():
        token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not token:
        sys.exit("BUCKY_API_TOKEN(또는 BUCKY_API_TOKEN_FILE)이 없어 기동을 거부합니다.")
    return token


AGENT_FIELDS = ("id", "type", "location", "role", "status")


def load_agents() -> dict[str, dict]:
    """agents.yaml을 id→agent dict로 로드. 형식 오류는 기동 거부(fail-fast).

    #2에 PyYAML이 없어 §21.2의 평탄 구조만 파싱한다:
    `agents:` 헤더 + `- key: value` 목록 항목 + `key: value` 필드. 주석(#)·빈 줄 허용.
    """
    if not AGENTS_FILE.is_file():
        sys.exit(f"Agent Registry 파일이 없어 기동을 거부합니다: {AGENTS_FILE}")
    agents: list[dict] = []
    current: dict | None = None
    in_agents = False
    # utf-8-sig: Windows 편집기가 붙이는 BOM이 첫 키 비교를 깨뜨리지 않게 흡수
    for lineno, raw in enumerate(AGENTS_FILE.read_text(encoding="utf-8-sig").splitlines(), 1):
        # YAML 규칙대로 공백이 앞선 #만 주석 — 값 속의 #(예: back#end)는 보존
        stripped = re.split(r"\s#", raw, maxsplit=1)[0].strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not in_agents:
            if stripped == "agents:":
                in_agents = True
                continue
            sys.exit(f"{AGENTS_FILE}:{lineno}: 'agents:' 목록으로 시작해야 합니다")
        if stripped.startswith("- "):
            current = {}
            agents.append(current)
            stripped = stripped[2:].strip()
        key, sep, value = stripped.partition(":")
        key = key.strip()
        if current is None or not sep or not key:
            sys.exit(f"{AGENTS_FILE}:{lineno}: 'key: value' 형식이 아닙니다: {raw.strip()!r}")
        if key in current:  # `- ` 누락으로 이전 블록에 병합된 경우도 여기서 잡힌다
            sys.exit(f"{AGENTS_FILE}:{lineno}: 키 중복: {key!r}")
        current[key] = value.strip().strip("'\"")
    registry: dict[str, dict] = {}
    for agent in agents:
        missing = [f for f in AGENT_FIELDS if not agent.get(f)]
        if missing:
            sys.exit(f"{AGENTS_FILE}: 에이전트 {agent.get('id', '?')!r}에 필수 필드 누락: {missing}")
        if agent["id"] in registry:
            sys.exit(f"{AGENTS_FILE}: 에이전트 id 중복: {agent['id']!r}")
        registry[agent["id"]] = agent
    if not registry:
        sys.exit(f"{AGENTS_FILE}: 등록된 에이전트가 없습니다")
    return registry


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS tasks (
                task_id      TEXT PRIMARY KEY,
                source       TEXT NOT NULL,
                requested_by TEXT NOT NULL,
                target_agent TEXT NOT NULL,
                task_type    TEXT NOT NULL,
                priority     TEXT NOT NULL,
                status       TEXT NOT NULL,
                payload      TEXT NOT NULL,
                result       TEXT,
                created_at   TEXT NOT NULL,
                updated_at   TEXT NOT NULL
            )"""
        )
        # /claim 폴링 핫패스 — 완료 태스크가 누적돼도 전체 스캔을 피한다.
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_claim ON tasks(status, target_agent)")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_task_id(now: datetime) -> str:
    return f"task_{now:%Y%m%d_%H%M%S}_{secrets.token_hex(2)}"


def row_to_task(row: sqlite3.Row) -> dict:
    task = dict(row)
    task["payload"] = json.loads(task["payload"])
    if task["result"] is not None:
        task["result"] = json.loads(task["result"])
    return task


def append_log(entry: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"api_{utc_now():%Y%m%d}.jsonl"
    with log_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


class BuckyAPIHandler(BaseHTTPRequestHandler):
    token: str = ""  # serve()에서 주입
    agents: dict[str, dict] = {}  # serve()에서 주입 — 정적 레지스트리(§21.2)
    # 헤더/바디 수신 대기 상한(초). 미완성 연결의 스레드 영구 점유(Slowloris) 차단.
    timeout = 15

    def log_message(self, fmt, *args):  # 기본 stderr 액세스 로그 대신 JSONL 사용
        pass

    def _safe(self, handler) -> None:
        try:
            handler()
        except Exception as exc:  # 예외 시에도 응답 없이 연결이 끊기지 않도록 500 보장
            try:
                append_log(
                    {
                        "ts": utc_now().isoformat(timespec="seconds"),
                        "method": self.command,
                        "path": self.path,
                        "error": repr(exc),
                        "remote": self.client_address[0],
                    }
                )
                self._send_json(500, {"error": "internal error"})
            except Exception:
                pass

    def _send_json(self, status: int, body: dict, task_id: str | None = None) -> None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        append_log(
            {
                "ts": utc_now().isoformat(timespec="seconds"),
                "method": self.command,
                "path": self.path,
                "status": status,
                "task_id": task_id,
                "remote": self.client_address[0],
            }
        )

    def _authorized(self) -> bool:
        header = self.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return False
        return hmac.compare_digest(header[len("Bearer "):].strip(), self.token)

    def do_GET(self) -> None:
        self._safe(self._handle_get)

    def do_POST(self) -> None:
        self._safe(self._handle_post)

    def _handle_get(self) -> None:
        if self.path == "/health":
            self._send_json(200, {"status": "ok"})
            return
        if self.path == "/api/v1/agents" or self.path.startswith("/api/v1/agents/"):
            if not self._authorized():
                self._send_json(401, {"error": "unauthorized"})
                return
            if self.path == "/api/v1/agents":
                self._send_json(200, {"agents": list(self.agents.values())})
                return
            agent_id = self.path[len("/api/v1/agents/"):]
            agent = self.agents.get(agent_id)
            if agent is None:
                self._send_json(404, {"error": "agent not found"})
                return
            self._send_json(200, agent)
            return
        if self.path.startswith("/api/v1/tasks/"):
            if not self._authorized():
                self._send_json(401, {"error": "unauthorized"})
                return
            task_id = self.path[len("/api/v1/tasks/"):]
            with closing(sqlite3.connect(DB_PATH)) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
            if row is None:
                self._send_json(404, {"error": "task not found"}, task_id=task_id)
                return
            self._send_json(200, row_to_task(row), task_id=task_id)
            return
        self._send_json(404, {"error": "not found"})

    def _handle_post(self) -> None:
        if not self.path.startswith("/api/v1/tasks"):
            self._send_json(404, {"error": "not found"})
            return
        if not self._authorized():
            self._send_json(401, {"error": "unauthorized"})
            return
        body = self._read_json_body()
        if body is None:
            return
        if self.path == "/api/v1/tasks":
            self._create_task(body)
            return
        if self.path == "/api/v1/tasks/claim":
            self._claim_task(body)
            return
        rest = self.path[len("/api/v1/tasks/"):]
        if rest.endswith("/status") and rest[: -len("/status")]:
            self._update_status(rest[: -len("/status")], body)
            return
        self._send_json(404, {"error": "not found"})

    def _read_json_body(self) -> dict | None:
        """본문을 dict로 파싱. 실패 시 에러 응답까지 보내고 None을 돌려준다."""
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if length < 0:  # 음수/비숫자 Content-Length로 rfile.read(-1) 영구 블로킹 방지
            self._send_json(400, {"error": "invalid content-length"})
            return None
        if length > MAX_BODY_BYTES:
            self._send_json(413, {"error": "body too large"})
            return None
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict):
                raise ValueError
        except (json.JSONDecodeError, ValueError):
            self._send_json(400, {"error": "invalid json body"})
            return None
        return body

    def _create_task(self, body: dict) -> None:
        task_type = str(body.get("task_type", "")).strip()
        if not task_type:
            self._send_json(400, {"error": "task_type is required"})
            return
        priority = body.get("priority", "normal")
        if priority not in PRIORITIES:
            self._send_json(400, {"error": f"priority must be one of {PRIORITIES}"})
            return
        payload = body.get("payload", {})
        if not isinstance(payload, dict):
            self._send_json(400, {"error": "payload must be an object"})
            return
        target_agent = str(body.get("target_agent", "bucky-main")).strip()
        if target_agent not in self.agents:  # 오타 에이전트로 영원히 클레임 안 되는 태스크 방지
            self._send_json(400, {"error": f"unknown target_agent: {target_agent}"})
            return

        now = utc_now()
        task_id = new_task_id(now)
        record = (
            task_id,
            str(body.get("source", "api")),
            str(body.get("requested_by", "unknown")),
            target_agent,
            task_type,
            priority,
            "pending",
            json.dumps(payload, ensure_ascii=False),
            None,
            now.isoformat(timespec="seconds"),
            now.isoformat(timespec="seconds"),
        )
        with closing(sqlite3.connect(DB_PATH)) as conn, conn:
            conn.execute("INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?,?)", record)
        self._send_json(201, {"task_id": task_id, "status": "pending"}, task_id=task_id)

    def _claim_task(self, body: dict) -> None:
        agent_id = str(body.get("agent_id", "")).strip()
        if not agent_id:
            self._send_json(400, {"error": "agent_id is required"})
            return
        if agent_id not in self.agents:
            self._send_json(400, {"error": f"unknown agent_id: {agent_id}"})
            return
        now = utc_now().isoformat(timespec="seconds")
        # 단일 UPDATE…RETURNING으로 선점을 원자화 — 동시 클레임이 같은 태스크를 집지 못한다.
        with closing(sqlite3.connect(DB_PATH)) as conn, conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """UPDATE tasks SET status = 'assigned', updated_at = ?
                   WHERE task_id = (
                       SELECT task_id FROM tasks
                       WHERE status = 'pending' AND target_agent = ?
                       ORDER BY CASE priority WHEN 'high' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END,
                                created_at, task_id
                       LIMIT 1
                   )
                   RETURNING *""",
                (now, agent_id),
            ).fetchone()
        if row is None:
            self._send_json(200, {"task": None})
            return
        self._send_json(200, {"task": row_to_task(row)}, task_id=row["task_id"])

    def _update_status(self, task_id: str, body: dict) -> None:
        new_status = str(body.get("status", "")).strip()
        if new_status not in STATUS_TARGETS:
            self._send_json(400, {"error": f"status must be one of {sorted(STATUS_TARGETS)}"})
            return
        result = body.get("result")
        if result is not None and not isinstance(result, dict):
            self._send_json(400, {"error": "result must be an object"})
            return
        now = utc_now().isoformat(timespec="seconds")
        with closing(sqlite3.connect(DB_PATH)) as conn:
            row = conn.execute("SELECT status FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
            if row is None:
                self._send_json(404, {"error": "task not found"}, task_id=task_id)
                return
            current = row[0]
            if new_status == current:  # 응답 유실 후 재전송 멱등 처리 — 이미 적용된 전이는 성공으로 응답
                self._send_json(200, {"task_id": task_id, "status": current}, task_id=task_id)
                return
            if new_status not in TRANSITIONS.get(current, set()):
                self._send_json(409, {"error": f"cannot transition {current} -> {new_status}"}, task_id=task_id)
                return
            with conn:  # AND status=? 가드 — 읽기와 갱신 사이에 다른 요청이 전이하면 경합으로 처리
                cur = conn.execute(
                    "UPDATE tasks SET status = ?, result = COALESCE(?, result), updated_at = ?"
                    " WHERE task_id = ? AND status = ?",
                    (
                        new_status,
                        json.dumps(result, ensure_ascii=False) if result is not None else None,
                        now,
                        task_id,
                        current,
                    ),
                )
            if cur.rowcount == 0:
                self._send_json(409, {"error": "concurrent update, retry"}, task_id=task_id)
                return
        self._send_json(200, {"task_id": task_id, "status": new_status}, task_id=task_id)


def serve(host: str, port: int) -> None:
    BuckyAPIHandler.token = load_token()
    BuckyAPIHandler.agents = load_agents()
    init_db()
    server = ThreadingHTTPServer((host, port), BuckyAPIHandler)
    print(f"Bucky Core API listening on {host}:{port} (db={DB_PATH}, agents={len(BuckyAPIHandler.agents)})")
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bucky Core API Server (Phase 3-①)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("BUCKY_API_PORT", 8700)))
    args = parser.parse_args()
    serve(args.host, args.port)
