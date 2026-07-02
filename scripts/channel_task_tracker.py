#!/usr/bin/env python3
"""Channel Task Tracker — 다중 채널 작업 영속 추적.

기능:
- 채널별 작업 저장 (SQLite)
- 중복 감지 (24h 내 유사 작업)
- 미완료/진행중/플랜 현황 요약
- !report 명령으로 전체 보고
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path

_ROOT = Path(__file__).parent.parent
DB_PATH = _ROOT / "data" / "channel_tasks.db"

STATUS_ICON = {
    "in_progress": "🔄",
    "pending":     "⏳",
    "done":        "✅",
    "failed":      "❌",
    "plan":        "📐",
}
STATUS_LABEL = {
    "in_progress": "진행중",
    "pending":     "대기",
    "done":        "완료",
    "failed":      "실패",
    "plan":        "플랜",
}
STATUS_ORDER = {"in_progress": 0, "pending": 1, "plan": 2, "done": 3, "failed": 4}


# ── DB 초기화 ─────────────────────────────────────────────────────────────────

def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS channel_tasks (
                id            TEXT PRIMARY KEY,
                channel_id    TEXT NOT NULL,
                channel_name  TEXT NOT NULL,
                content       TEXT NOT NULL,
                status        TEXT NOT NULL DEFAULT 'in_progress',
                result_summary TEXT,
                created_at    TEXT NOT NULL,
                updated_at    TEXT NOT NULL
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_created ON channel_tasks(created_at)"
        )


# ── CRUD ─────────────────────────────────────────────────────────────────────

def save_task(channel_id: str, channel_name: str, content: str,
              status: str = "in_progress") -> str:
    """새 작업 저장 → task_id 반환."""
    init_db()
    task_id = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat(timespec="seconds")
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO channel_tasks VALUES (?,?,?,?,?,?,?,?)",
            (task_id, channel_id, channel_name, content, status, None, now, now),
        )
    return task_id


def update_task(task_id: str, status: str, result_summary: str | None = None) -> None:
    init_db()
    now = datetime.now().isoformat(timespec="seconds")
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE channel_tasks SET status=?, result_summary=?, updated_at=? WHERE id=?",
            (status, result_summary, now, task_id),
        )


def mark_plan(channel_id: str, channel_name: str, content: str) -> str:
    """플랜 항목으로 저장."""
    return save_task(channel_id, channel_name, content, status="plan")


# ── 중복 감지 ─────────────────────────────────────────────────────────────────

def find_duplicates(content: str, exclude_id: str | None = None,
                    hours: int = 24, threshold: float = 0.45) -> list[dict]:
    """최근 N시간 내 유사 작업 탐지 (키워드 오버랩)."""
    init_db()
    words = set(w for w in content.lower().split() if len(w) > 1)
    if not words:
        return []
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """SELECT id, channel_name, content, status FROM channel_tasks
               WHERE created_at > ? AND status NOT IN ('done','failed')
               ORDER BY created_at DESC LIMIT 100""",
            (cutoff,),
        ).fetchall()

    dupes: list[dict] = []
    for row_id, ch_name, row_content, row_status in rows:
        if row_id == exclude_id:
            continue
        row_words = set(w for w in row_content.lower().split() if len(w) > 1)
        if not row_words:
            continue
        overlap = len(words & row_words) / max(len(words), len(row_words))
        if overlap >= threshold:
            dupes.append({
                "id": row_id, "channel": ch_name,
                "content": row_content, "status": row_status,
                "overlap": round(overlap, 2),
            })
    return dupes


# ── 현황 보고 ─────────────────────────────────────────────────────────────────

def get_report(days: int = 7) -> str:
    """전체 채널 작업 현황 요약 (Discord 마크다운)."""
    init_db()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """SELECT channel_name, content, status, result_summary, created_at, updated_at
               FROM channel_tasks WHERE created_at > ?
               ORDER BY updated_at DESC LIMIT 60""",
            (cutoff,),
        ).fetchall()

    if not rows:
        return f"📋 최근 {days}일 기록된 작업 없음"

    by_status: dict[str, list] = {}
    for ch, content, status, result, created, updated in rows:
        by_status.setdefault(status, []).append((ch, content, result, updated))

    lines = [f"📋 **다중채널 작업 현황** (최근 {days}일)\n"]
    for status in ("in_progress", "pending", "plan", "done", "failed"):
        items = by_status.get(status)
        if not items:
            continue
        icon  = STATUS_ICON[status]
        label = STATUS_LABEL[status]
        lines.append(f"**{icon} {label} ({len(items)})**")
        for ch, content, result, updated in items:
            short = content[:70] + ("…" if len(content) > 70 else "")
            lines.append(f"  `#{ch}` {short}")
            if result:
                rsummary = result[:60] + ("…" if len(result) > 60 else "")
                lines.append(f"    ↳ {rsummary}")
        lines.append("")

    # 미완료 합계
    incomplete = sum(
        len(by_status.get(s, []))
        for s in ("in_progress", "pending", "plan")
    )
    done  = len(by_status.get("done", []))
    failed = len(by_status.get("failed", []))
    lines.append(
        f"─\n🔢 미완료 **{incomplete}** · 완료 **{done}** · 실패 **{failed}**"
    )
    return "\n".join(lines)


def get_channel_history(channel_id: str, limit: int = 10) -> str:
    """특정 채널 최근 작업 목록."""
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """SELECT content, status, result_summary, updated_at
               FROM channel_tasks WHERE channel_id=?
               ORDER BY updated_at DESC LIMIT ?""",
            (channel_id, limit),
        ).fetchall()

    if not rows:
        return "이 채널에 기록된 작업 없음"

    lines = [f"📂 **이 채널 최근 {limit}개 작업**\n"]
    for content, status, result, updated in rows:
        icon = STATUS_ICON.get(status, "•")
        short = content[:60] + ("…" if len(content) > 60 else "")
        lines.append(f"{icon} {short}")
        if result:
            lines.append(f"  ↳ {result[:60]}{'…' if len(result)>60 else ''}")
    return "\n".join(lines)
