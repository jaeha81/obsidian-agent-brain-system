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
load_dotenv(_ROOT / ".env", encoding="utf-8", override=True)

VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
DB_PATH = VAULT / "10_AgentBus" / "tasks" / "bucky_memory.db"
CONTEXT_FILE = VAULT / "00_System" / "BUCKY_CONTEXT.md"
MAX_HISTORY = int(os.getenv("BUCKY_MAX_HISTORY", "30"))

_lock = threading.Lock()
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
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                channel   TEXT NOT NULL,
                role      TEXT NOT NULL,
                content   TEXT NOT NULL,
                ts        TEXT NOT NULL
            )
        """)
        _conn.execute("""
            CREATE TABLE IF NOT EXISTS learned_facts (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                fact     TEXT NOT NULL,
                source   TEXT,
                ts       TEXT NOT NULL
            )
        """)
        _conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_channel ON conv_history(channel, id)")
        _conn.commit()
    return _conn


# ── 대화 영속화 ────────────────────────────────────────────────────────────────

def save_message(channel: str, role: str, content: str) -> None:
    with _lock:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO conv_history (channel, role, content, ts) VALUES (?,?,?,?)",
            (channel, role, content[:4000], datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
        # 채널별 MAX_HISTORY*2 초과 시 오래된 것 정리
        conn.execute("""
            DELETE FROM conv_history WHERE channel=? AND id NOT IN (
                SELECT id FROM conv_history WHERE channel=? ORDER BY id DESC LIMIT ?
            )
        """, (channel, channel, MAX_HISTORY * 2))
        conn.commit()


def load_history(channel: str, limit: int = MAX_HISTORY) -> list[dict]:
    with _lock:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT role, content FROM conv_history WHERE channel=? ORDER BY id DESC LIMIT ?",
            (channel, limit),
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


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
        raw = run_bucky(_EXTRACT_PROMPT.format(conversation=conversation[:3000]), timeout=30)
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


def append_to_context(facts: list[dict]) -> None:
    """추출된 사실을 BUCKY_CONTEXT.md 자동학습 섹션에 추가."""
    if not facts or not CONTEXT_FILE.exists():
        return
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
