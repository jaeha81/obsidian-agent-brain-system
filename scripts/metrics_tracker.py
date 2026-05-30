#!/usr/bin/env python3
"""
metrics_tracker.py — Card 5: 측정 이벤트 + SQL 체크리스트

측정 이벤트를 SQLite에 기록하고 체크리스트 형태로 조회한다.

사용법:
    python scripts/metrics_tracker.py log <event_type> <detail>
    python scripts/metrics_tracker.py events [--limit N]
    python scripts/metrics_tracker.py checklist
    python scripts/metrics_tracker.py summary
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "metrics.db"

# 체크리스트 SQL — 시스템 건강도 지표
CHECKLIST_QUERIES = {
    "오늘 완료 태스크": """
        SELECT COUNT(*) FROM events
        WHERE event_type = 'task_complete'
          AND ts >= date('now')
    """,
    "오늘 게이트 통과": """
        SELECT COUNT(*) FROM events
        WHERE event_type = 'gate_pass'
          AND ts >= date('now')
    """,
    "오늘 게이트 실패": """
        SELECT COUNT(*) FROM events
        WHERE event_type = 'gate_fail'
          AND ts >= date('now')
    """,
    "이번 주 Bucky 패킷 생성": """
        SELECT COUNT(*) FROM events
        WHERE event_type = 'packet_generated'
          AND ts >= date('now', '-7 days')
    """,
    "이번 주 승인 대기 태스크": """
        SELECT COUNT(*) FROM events
        WHERE event_type = 'task_pending_approval'
          AND ts >= date('now', '-7 days')
    """,
    "이번 주 Vault YAML 오류": """
        SELECT COUNT(*) FROM events
        WHERE event_type = 'yaml_error'
          AND ts >= date('now', '-7 days')
    """,
    "총 이벤트 수": """
        SELECT COUNT(*) FROM events
    """,
}

EVENT_TYPES = {
    "task_complete": "태스크 완료",
    "task_pending_approval": "승인 대기",
    "gate_pass": "게이트 통과",
    "gate_fail": "게이트 실패",
    "packet_generated": "Bucky 패킷 생성",
    "yaml_error": "Vault YAML 오류",
    "smoke_pass": "스모크 테스트 통과",
    "smoke_fail": "스모크 테스트 실패",
    "runbook_exported": "런북 내보내기",
    "agent_started": "에이전트 시작",
    "agent_stopped": "에이전트 중단",
    "codex_review": "Codex 검수 완료",
    "wishket_proposal": "Wishket 제안서 생성",
}


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            event_type TEXT NOT NULL,
            detail TEXT
        )
    """)
    conn.commit()
    return conn


def log_event(event_type: str, detail: str = "") -> int:
    """이벤트를 DB에 기록하고 새 row ID를 반환한다."""
    with _get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO events (event_type, detail) VALUES (?, ?)",
            (event_type, detail)
        )
        return cur.lastrowid


def cmd_log(event_type: str, detail: str) -> None:
    row_id = log_event(event_type, detail)
    label = EVENT_TYPES.get(event_type, event_type)
    print(f"✅ 기록됨 #{row_id} [{label}] {detail}")


def cmd_events(limit: int = 20) -> None:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT ts, event_type, detail FROM events ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    if not rows:
        print("이벤트 없음")
        return
    print(f"\n── 최근 이벤트 (최대 {limit}개) ──────────────────────")
    for ts, etype, detail in rows:
        label = EVENT_TYPES.get(etype, etype)
        print(f"  {ts}  {label:<18} {detail or ''}")
    print()


def cmd_checklist() -> None:
    conn = _get_conn()
    print("\n── 시스템 건강도 체크리스트 ────────────────────────")
    all_ok = True
    for label, query in CHECKLIST_QUERIES.items():
        try:
            count = conn.execute(query).fetchone()[0]
        except Exception as e:
            count = f"ERR({e})"
            all_ok = False
        icon = "✅" if isinstance(count, int) and count >= 0 else "⚠️"
        print(f"  {icon}  {label:<24} {count}")
    print(f"\n  전체: {'✅ 정상' if all_ok else '⚠️ 확인 필요'}")
    print()


def cmd_summary() -> None:
    conn = _get_conn()
    rows = conn.execute("""
        SELECT event_type, COUNT(*) as cnt
        FROM events
        GROUP BY event_type
        ORDER BY cnt DESC
    """).fetchall()
    print("\n── 이벤트 유형별 집계 ──────────────────────────────")
    for etype, cnt in rows:
        label = EVENT_TYPES.get(etype, etype)
        print(f"  {label:<24} {cnt:>5}회")
    print()


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    p_log = sub.add_parser("log", help="이벤트 기록")
    p_log.add_argument("event_type", choices=list(EVENT_TYPES.keys()))
    p_log.add_argument("detail", nargs="?", default="")

    p_ev = sub.add_parser("events", help="최근 이벤트 조회")
    p_ev.add_argument("--limit", type=int, default=20)

    sub.add_parser("checklist", help="체크리스트 조회")
    sub.add_parser("summary", help="유형별 집계")

    args = ap.parse_args()

    if args.cmd == "log":
        cmd_log(args.event_type, args.detail)
    elif args.cmd == "events":
        cmd_events(args.limit)
    elif args.cmd == "checklist":
        cmd_checklist()
    elif args.cmd == "summary":
        cmd_summary()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
