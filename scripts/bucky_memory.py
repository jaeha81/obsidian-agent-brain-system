#!/usr/bin/env python3
"""
Bucky 장기 기억 시스템.

1. SQLite 대화 영속화 — 봇 재시작 후에도 채널별 대화 복원
2. 자동 사실 추출 — 대화에서 프로젝트·결정·목표 감지 → BUCKY_CONTEXT 자동 기록
"""

import json
import os
import re
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env", encoding="utf-8-sig", override=True)

VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
_DB_PATH_OVERRIDE = os.getenv("BUCKY_MEMORY_DB_PATH", "").strip()
DB_PATH = Path(_DB_PATH_OVERRIDE) if _DB_PATH_OVERRIDE else VAULT / "10_AgentBus" / "tasks" / "bucky_memory.db"
CONTEXT_FILE = VAULT / "00_System" / "BUCKY_CONTEXT.md"
MAX_HISTORY = int(os.getenv("BUCKY_MAX_HISTORY", "30"))

SESSION_GAP_MINUTES = int(os.getenv("BUCKY_SESSION_GAP", "90"))

_lock = threading.RLock()  # RLock: 같은 스레드의 재진입 허용 (세션 함수 중첩 호출 대비)
_conn: Optional[sqlite3.Connection] = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("""
            CREATE TABLE IF NOT EXISTS conv_history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                channel    TEXT NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                ts         TEXT NOT NULL,
                session_id INTEGER DEFAULT NULL
            )
        """)
        # 기존 DB 마이그레이션: session_id 컬럼 없으면 추가
        try:
            _conn.execute("ALTER TABLE conv_history ADD COLUMN session_id INTEGER DEFAULT NULL")
            _conn.commit()
        except Exception:
            pass  # 이미 존재
        _conn.execute("""
            CREATE TABLE IF NOT EXISTS learned_facts (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                fact     TEXT NOT NULL,
                source   TEXT,
                ts       TEXT NOT NULL
            )
        """)
        _conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                channel TEXT NOT NULL,
                started TEXT NOT NULL,
                ended   TEXT DEFAULT '',
                external_key TEXT DEFAULT '',
                label   TEXT DEFAULT ''
            )
        """)
        for ddl in (
            "ALTER TABLE sessions ADD COLUMN external_key TEXT DEFAULT ''",
            "ALTER TABLE sessions ADD COLUMN label TEXT DEFAULT ''",
        ):
            try:
                _conn.execute(ddl)
                _conn.commit()
            except Exception:
                pass
        _conn.execute("""
            CREATE TABLE IF NOT EXISTS active_sessions (
                channel    TEXT PRIMARY KEY,
                session_id INTEGER NOT NULL,
                updated    TEXT NOT NULL
            )
        """)
        _conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_channel ON conv_history(channel, id)")
        _conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_session ON conv_history(session_id, id)")
        _conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_channel ON sessions(channel, id)")
        _conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_external ON sessions(channel, external_key)")
        _conn.commit()
    return _conn


# ── 세션 관리 ──────────────────────────────────────────────────────────────────

def _set_active_session(conn: sqlite3.Connection, channel: str, session_id: int) -> None:
    conn.execute(
        """
        INSERT INTO active_sessions (channel, session_id, updated)
        VALUES (?, ?, ?)
        ON CONFLICT(channel) DO UPDATE SET
            session_id=excluded.session_id,
            updated=excluded.updated
        """,
        (channel, session_id, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()


def get_active_session(channel: str, gap_minutes: int = SESSION_GAP_MINUTES) -> int:
    """현재 활성 세션 ID 반환. 마지막 메시지가 gap_minutes 초과 시 자동으로 새 세션 생성."""
    with _lock:
        conn = _get_conn()
        active = conn.execute(
            "SELECT session_id FROM active_sessions WHERE channel=?",
            (channel,),
        ).fetchone()
        if active:
            session_id = int(active["session_id"])
            exists = conn.execute(
                "SELECT id FROM sessions WHERE channel=? AND id=?",
                (channel, session_id),
            ).fetchone()
            if exists:
                last_msg = conn.execute(
                    "SELECT ts FROM conv_history WHERE session_id=? ORDER BY id DESC LIMIT 1",
                    (session_id,),
                ).fetchone()
                if not last_msg:
                    return session_id
                gap = (datetime.now() - datetime.fromisoformat(last_msg["ts"])).total_seconds() / 60
                if gap < gap_minutes:
                    return session_id

        row = conn.execute(
            "SELECT id FROM sessions WHERE channel=? ORDER BY id DESC LIMIT 1",
            (channel,),
        ).fetchone()

        if row:
            session_id = row["id"]
            last_msg = conn.execute(
                "SELECT ts FROM conv_history WHERE session_id=? ORDER BY id DESC LIMIT 1",
                (session_id,),
            ).fetchone()
            if not last_msg:
                return session_id  # 빈 세션 재사용
            gap = (datetime.now() - datetime.fromisoformat(last_msg["ts"])).total_seconds() / 60
            if gap < gap_minutes:
                _set_active_session(conn, channel, session_id)
                return session_id

        cur = conn.execute(
            "INSERT INTO sessions (channel, started) VALUES (?, ?)",
            (channel, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
        _set_active_session(conn, channel, cur.lastrowid)
        return cur.lastrowid


def new_session(channel: str) -> int:
    """채널에 강제로 새 세션을 생성하고 ID를 반환."""
    with _lock:
        conn = _get_conn()
        cur = conn.execute(
            "INSERT INTO sessions (channel, started) VALUES (?, ?)",
            (channel, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
        _set_active_session(conn, channel, cur.lastrowid)
        return cur.lastrowid


def resume_session(channel: str, session_id: int) -> bool:
    """Set an existing channel session as the active continuation target."""
    with _lock:
        conn = _get_conn()
        row = conn.execute(
            "SELECT id FROM sessions WHERE channel=? AND id=?",
            (channel, session_id),
        ).fetchone()
        if not row:
            return False
        _set_active_session(conn, channel, session_id)
        return True


def get_or_create_session_for_key(channel: str, external_key: str, label: str = "") -> int:
    """Return and activate a stable per-dashboard-item session."""
    clean_key = (external_key or "").strip()
    clean_label = (label or "").strip()
    if not clean_key:
        return get_active_session(channel)
    with _lock:
        conn = _get_conn()
        row = conn.execute(
            "SELECT id FROM sessions WHERE channel=? AND external_key=? ORDER BY id DESC LIMIT 1",
            (channel, clean_key),
        ).fetchone()
        if row:
            session_id = int(row["id"])
            if clean_label:
                conn.execute(
                    "UPDATE sessions SET label=? WHERE id=?",
                    (clean_label[:200], session_id),
                )
                conn.commit()
            _set_active_session(conn, channel, session_id)
            return session_id
        cur = conn.execute(
            "INSERT INTO sessions (channel, started, external_key, label) VALUES (?, ?, ?, ?)",
            (
                channel,
                datetime.now().isoformat(timespec="seconds"),
                clean_key[:240],
                clean_label[:200],
            ),
        )
        conn.commit()
        _set_active_session(conn, channel, cur.lastrowid)
        return cur.lastrowid


def list_sessions(channel: str, limit: int = 10) -> list[dict]:
    """채널의 최근 세션 목록 반환 (최신 순)."""
    with _lock:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT id, started, external_key, label FROM sessions WHERE channel=? ORDER BY id DESC LIMIT ?",
            (channel, limit),
        ).fetchall()
        result = []
        for r in rows:
            first = conn.execute(
                "SELECT content FROM conv_history WHERE session_id=? AND role='user' ORDER BY id LIMIT 1",
                (r["id"],),
            ).fetchone()
            count = conn.execute(
                "SELECT COUNT(*) as cnt FROM conv_history WHERE session_id=?",
                (r["id"],),
            ).fetchone()
            preview = ""
            if first:
                txt = first["content"]
                preview = txt[:60] + "..." if len(txt) > 60 else txt
            result.append({
                "id": r["id"],
                "started": r["started"],
                "first_msg": preview,
                "count": count["cnt"] if count else 0,
                "external_key": r["external_key"] or "",
                "label": r["label"] or "",
            })
        return result


def load_session_history(channel: str, session_id: int, limit: int = MAX_HISTORY) -> list[dict]:
    """특정 세션의 대화 기록 반환 (오래된 것 먼저)."""
    with _lock:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT role, content FROM conv_history WHERE channel=? AND session_id=? ORDER BY id DESC LIMIT ?",
            (channel, session_id, limit),
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def get_prev_session_context(channel: str, current_session_id: int, n_msgs: int = 4) -> str:
    """이전 세션의 마지막 N개 메시지를 요약 형태로 반환. 새 세션 시작 시 컨텍스트 연결용."""
    with _lock:
        conn = _get_conn()
        row = conn.execute(
            "SELECT id, started FROM sessions WHERE channel=? AND id < ? ORDER BY id DESC LIMIT 1",
            (channel, current_session_id),
        ).fetchone()
        if not row:
            return ""
        rows = conn.execute(
            "SELECT role, content FROM conv_history WHERE session_id=? ORDER BY id DESC LIMIT ?",
            (row["id"], n_msgs),
        ).fetchall()
        if not rows:
            return ""
        ts = row["started"][:16]
        lines = [f"[이전 세션 {ts} 요약]"]
        for r in reversed(rows):
            snippet = r["content"][:200] + ("..." if len(r["content"]) > 200 else "")
            lines.append(f"{r['role'].title()}: {snippet}")
        return "\n".join(lines)


# ── 대화 영속화 ────────────────────────────────────────────────────────────────

def save_message(channel: str, role: str, content: str) -> None:
    session_id = get_active_session(channel)
    with _lock:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO conv_history (channel, role, content, ts, session_id) VALUES (?,?,?,?,?)",
            (channel, role, content[:4000], datetime.now().isoformat(timespec="seconds"), session_id),
        )
        conn.commit()
        # 채널 전체에서 오래된 것 정리 (세션 여러 개 보존을 위해 4x)
        conn.execute("""
            DELETE FROM conv_history WHERE channel=? AND id NOT IN (
                SELECT id FROM conv_history WHERE channel=? ORDER BY id DESC LIMIT ?
            )
        """, (channel, channel, MAX_HISTORY * 4))
        conn.commit()


def load_history(channel: str, limit: int = MAX_HISTORY) -> list[dict]:
    """현재 활성 세션의 대화 기록 반환."""
    session_id = get_active_session(channel)
    return load_session_history(channel, session_id, limit)


def clear_history(channel: str) -> None:
    with _lock:
        conn = _get_conn()
        conn.execute("DELETE FROM conv_history WHERE channel=?", (channel,))
        conn.commit()


# ── 자동 사실 추출 ─────────────────────────────────────────────────────────────

_EXTRACT_PROMPT = """\
아래 대화에서 Bucky가 기억해야 할 새로운 사실을 추출해라.
추출 대상: 프로젝트 정보, URL/경로, 사업 목표, 기술 결정, 중요 지시사항.
이미 알고 있을 법한 일반적인 내용은 제외.

JSON 배열로만 응답. 다른 텍스트 없음.
형식: [{{"category": "project|goal|tech|instruction", "fact": "내용"}}]
사실 없으면: []

대화:
{conversation}
"""


def extract_facts(conversation: str) -> list[dict]:
    """대화에서 기억할 사실 추출 — Claude 사용."""
    try:
        from bucky_client import run_bucky
        # task_type='extract' → Haiku 라우팅 (Sonnet 한도 절약)
        raw = run_bucky(
            _EXTRACT_PROMPT.format(conversation=conversation[:3000]),
            timeout=30,
            task_type="extract",
        )
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start != -1 and end > start:
            facts = json.loads(raw[start:end])
            if isinstance(facts, list):
                return facts[:10]
    except Exception as e:
        print(f"[Memory] 사실 추출 실패: {e}", flush=True)
    return []


def save_facts(facts: list[dict], source: str = "auto") -> None:
    if not facts:
        return
    with _lock:
        conn = _get_conn()
        now = datetime.now().isoformat(timespec="seconds")
        for f in facts:
            category = f.get("category", "misc")
            fact = f.get("fact", "").strip()
            if fact:
                conn.execute(
                    "INSERT INTO learned_facts (category, fact, source, ts) VALUES (?,?,?,?)",
                    (category, fact, source, now),
                )
        conn.commit()


def get_recent_facts(limit: int = 20) -> list[dict]:
    with _lock:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT category, fact, ts FROM learned_facts ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"category": r["category"], "fact": r["fact"], "ts": r["ts"]} for r in rows]


_ctx_lock = threading.Lock()


def append_to_context(facts: list[dict]) -> None:
    """추출된 사실을 BUCKY_CONTEXT.md 자동학습 섹션에 추가."""
    if not facts or not CONTEXT_FILE.exists():
        return
    with _ctx_lock:
        try:
            content = CONTEXT_FILE.read_text(encoding="utf-8")
            section = "\n\n## 🧠 자동 학습된 사실 (Auto-Memory)\n\n"
            new_lines = []
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            for f in facts:
                icon = {"project": "🚀", "goal": "🎯", "tech": "⚙️", "instruction": "📌"}.get(f.get("category", ""), "•")
                new_lines.append(f"- {icon} [{now}] {f['fact']}")

            if "## 🧠 자동 학습된 사실" in content:
                content = content + "\n".join(new_lines) + "\n"
            else:
                content = content + section + "\n".join(new_lines) + "\n"

            CONTEXT_FILE.write_text(content, encoding="utf-8")
            print(f"[Memory] {len(facts)}개 사실 → BUCKY_CONTEXT 기록", flush=True)
        except Exception as e:
            print(f"[Memory] context 기록 실패: {e}", flush=True)
            return

    try:
        from bucky_memory_compactor import compact as _compact
        threshold_kb = int(os.getenv("BUCKY_CONTEXT_THRESHOLD_KB", "50"))
        keep_entries = int(os.getenv("BUCKY_CONTEXT_KEEP_ENTRIES", "30"))
        result = _compact(
            context_file=CONTEXT_FILE,
            threshold_kb=threshold_kb,
            keep_entries=keep_entries,
            dry_run=False,
            force=False,
        )
        if result.get("triggered"):
            print(
                f"[Memory] auto-compaction triggered: archived={result.get('archived', 0)} "
                f"kept={result.get('kept', 0)} → {result.get('archive_path')}",
                flush=True,
            )
    except Exception as e:
        print(f"[Memory] auto-compaction skipped: {e}", flush=True)
