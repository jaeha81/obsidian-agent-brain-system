#!/usr/bin/env python3
"""
SQLite-based concurrent task queue for Bucky multi-task orchestration.
10개 동시 태스크 지원. 기존 task_tracker.py(JSON) 와 병행 운영.
"""

import os
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env", encoding="utf-8", override=True)

VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
DB_PATH = VAULT / "10_AgentBus" / "tasks" / "bucky_tasks.db"

_lock = threading.Lock()
_conn: Optional[sqlite3.Connection] = None

# ── 라우팅 키워드 (v2: Codex=2번구현자, Claude=1번구현자) ─────────────────────
# Codex: 백엔드·스크립트·API·테스트·자동화·DB·버그수정·리팩토링
_CODEX_KEYWORDS = (
    "백엔드", "backend", "서버", "server", "api", "endpoint",
    "스크립트", "script", "스크립트 작성", "자동화", "automation", "배치", "batch", "크론", "cron",
    "파이썬", "python", "shell",
    "데이터베이스", "database", "db", "쿼리", "query", "마이그레이션", "migration",
    "테스트", "test", "pytest", "테스트 작성", "단위테스트", "unit test",
    "버그", "bug", "오류", "error", "디버깅", "debug", "버그수정", "fix", "수정해",
    "리팩토링", "refactor",
    "데이터 처리", "파싱", "parsing", "크롤링", "crawl",
    "검수", "코드 리뷰", "code review",
)
# Claude Code: 프론트엔드·UI·복잡한 구현·아키텍처·전략
_CLAUDE_KEYWORDS = (
    "프론트엔드", "frontend", "html", "css", "javascript", "js", "react", "vue",
    "ui", "ux", "디자인", "레이아웃", "layout", "컴포넌트", "component",
    "페이지", "page", "대시보드", "dashboard", "차트", "chart",
    "구현", "구현해", "만들어", "개발해", "implement", "create", "build", "추가해",
    "아키텍처", "architecture", "설계", "시스템", "전략", "strategy", "prd",
    "분석", "왜", "explain", "why", "조사",
)
_CHRIS_KEYWORDS = (
    "chris", "크리스", "graphify", "그래피파이", "그래프파이", "지식 그래프",
    "knowledge graph", "지식 구조", "지식 정리", "브레인 성능", "연결성",
    "고립 노드", "isolated node", "context pack 후보", "컨텍스트팩 후보",
    "지식 갭", "knowledge gap",
)


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA synchronous=NORMAL")
        _conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id       TEXT PRIMARY KEY,
                title    TEXT NOT NULL,
                body     TEXT NOT NULL,
                agent    TEXT NOT NULL,
                status   TEXT NOT NULL DEFAULT 'pending',
                created  TEXT NOT NULL,
                updated  TEXT,
                result   TEXT,
                source   TEXT DEFAULT 'user'
            )
        """)
        _conn.commit()
    return _conn


def _next_id() -> str:
    """Return the next numeric task id without reusing existing T### ids.

    Older repaired/imported rows can have dates outside today's window while
    still occupying ids such as T001, so the allocator must not filter by date.
    """
    conn = _get_conn()
    row = conn.execute(
        "SELECT MAX(CAST(SUBSTR(id,2) AS INTEGER)) FROM tasks "
        "WHERE id GLOB 'T[0-9]*'"
    ).fetchone()
    n = (row[0] if row and row[0] is not None else 0) + 1
    return f"T{n:03d}"


def route(body: str, force_agent: Optional[str] = None) -> str:
    """키워드 기반 자동 라우팅 → codex(2번구현자) / claude(1번구현자) / bucky"""
    if force_agent and force_agent in ("codex", "claude", "bucky", "chris"):
        return force_agent
    b = body.lower()
    chris_score = sum(1 for k in _CHRIS_KEYWORDS if k in b)
    codex_score = sum(1 for k in _CODEX_KEYWORDS if k in b)
    claude_score = sum(1 for k in _CLAUDE_KEYWORDS if k in b)
    if chris_score > max(codex_score, claude_score):
        return "chris"
    if codex_score > claude_score:
        return "codex"
    if claude_score > 0:
        return "claude"
    return "bucky"


def add(title: str, body: str, agent: Optional[str] = None, source: str = "discord") -> dict:
    """새 태스크 등록. agent 미지정 시 키워드 자동 라우팅.

    IntegrityError(UNIQUE 충돌) 발생 시 ID를 재계산해 최대 3회 재시도.
    """
    with _lock:
        conn = _get_conn()
        assigned = route(body, agent)
        now = datetime.now().isoformat(timespec="seconds")
        for attempt in range(3):
            tid = _next_id()
            try:
                conn.execute(
                    "INSERT INTO tasks (id,title,body,agent,status,created,source) VALUES (?,?,?,?,?,?,?)",
                    (tid, title[:80], body, assigned, "pending", now, source),
                )
                conn.commit()
                break
            except sqlite3.IntegrityError:
                # ID 충돌 시 DB를 다시 조회해 다음 ID 재계산 후 재시도
                print(f"[TaskQueue] ID 충돌 {tid} — 재시도 {attempt+1}/3", flush=True)
                conn.rollback()
                if attempt == 2:
                    raise
    return {"id": tid, "title": title[:80], "body": body, "agent": assigned,
            "status": "pending", "created": now, "source": source}


def update(task_id: str, status: str, result: Optional[str] = None) -> bool:
    with _lock:
        conn = _get_conn()
        now = datetime.now().isoformat(timespec="seconds")
        if result is not None:
            conn.execute(
                "UPDATE tasks SET status=?,updated=?,result=? WHERE id=?",
                (status, now, result[:600] if result else None, task_id),
            )
        else:
            conn.execute(
                "UPDATE tasks SET status=?,updated=? WHERE id=?",
                (status, now, task_id),
            )
        conn.commit()
        return conn.execute("SELECT changes()").fetchone()[0] > 0


def get(task_id: str) -> Optional[dict]:
    with _lock:
        conn = _get_conn()
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return dict(row) if row else None


def get_active() -> list:
    with _lock:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT * FROM tasks WHERE status IN ('pending','in_progress','submitted') ORDER BY created"
        ).fetchall()
        return [dict(r) for r in rows]


def get_today() -> list:
    with _lock:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT * FROM tasks WHERE date(created,'localtime')=date('now','localtime') ORDER BY created DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def format_dashboard(tasks: Optional[list] = None) -> str:
    if tasks is None:
        tasks = get_today()
    if not tasks:
        return "오늘 등록된 태스크 없음"

    status_icon = {
        "pending": "⏳", "in_progress": "🔄", "submitted": "📤",
        "done": "✅", "failed": "❌",
    }
    agent_icon = {"claude": "🧠", "codex": "⚡", "bucky": "🤖", "chris": "🧭"}

    lines = ["**📋 Bucky 태스크 현황**\n"]
    for t in tasks:
        icon = status_icon.get(t.get("status", ""), "❓")
        a_icon = agent_icon.get(t.get("agent", ""), "")
        lines.append(f"{icon} `{t['id']}` {a_icon} **{t['title'][:50]}**")
        if t.get("result"):
            lines.append(f"   └ {t['result'][:100]}")

    done = sum(1 for t in tasks if t.get("status") == "done")
    submitted = sum(1 for t in tasks if t.get("status") == "submitted")
    failed = sum(1 for t in tasks if t.get("status") == "failed")
    active = sum(1 for t in tasks if t.get("status") == "in_progress")
    pending = sum(1 for t in tasks if t.get("status") == "pending")
    lines.append(
        f"\n✅{done} | 🔄{active} | ⏳{pending} | 📤{submitted} | ❌{failed}  —  총 {len(tasks)}개"
    )
    return "\n".join(lines)
