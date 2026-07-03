#!/usr/bin/env python3
"""prompt_logger.py — Claude Code 사용자 프롬프트 전문 기록

UserPromptSubmit 훅에서 호출됨. 전문을 날짜별 마크다운 로그로 저장.
bucky_awareness.py(JSONL 400자 미리보기)와 달리 전문 + 프로젝트 컨텍스트 보존.

출력: ObsidianVault/10_AgentBus/promptlog/YYYY-MM-DD.md
conv_history: 읽기 전용 — 필요 시 최근 Bucky 컨텍스트 조회용으로만 사용.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
VAULT = ROOT / "ObsidianVault"
PROMPTLOG_DIR = VAULT / "10_AgentBus" / "promptlog"
DB_PATH = VAULT / "10_AgentBus" / "tasks" / "bucky_memory.db"

MAX_BUCKY_CONTEXT = 2  # 최근 Bucky 메시지 포함 개수 (0이면 생략)


def _get_recent_bucky(channel: str | None = None) -> list[str]:
    """conv_history에서 최근 assistant 메시지 N건 조회 (읽기 전용)."""
    if MAX_BUCKY_CONTEXT == 0 or not DB_PATH.exists():
        return []
    try:
        import sqlite3
        con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        cur = con.cursor()
        where = "WHERE role='assistant'"
        if channel:
            where += f" AND channel='{channel}'"
        cur.execute(
            f"SELECT content FROM conv_history {where} ORDER BY id DESC LIMIT ?",
            (MAX_BUCKY_CONTEXT,),
        )
        rows = cur.fetchall()
        con.close()
        return [r[0][:200] for r in rows]
    except Exception:
        return []


def main() -> None:
    if os.environ.get("BUCKY_SUBPROCESS") == "1":
        return
    if os.environ.get("CLAUDE_HOOK_EVENT", "") != "UserPromptSubmit":
        return

    try:
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        return

    prompt = data.get("prompt", "").strip()
    if not prompt:
        return

    ts = datetime.now()
    cwd = os.getcwd()
    project = Path(cwd).name
    session_id = data.get("session_id", "")
    sid_short = session_id[:8] if session_id else ""

    PROMPTLOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = PROMPTLOG_DIR / f"{ts.strftime('%Y-%m-%d')}.md"

    # 최근 Bucky 컨텍스트 (선택적)
    bucky_lines = _get_recent_bucky()
    bucky_block = ""
    if bucky_lines:
        bucky_block = "\n> **Bucky 최근 응답**\n" + "\n".join(
            f"> {b.replace(chr(10), ' ')[:120]}" for b in bucky_lines
        ) + "\n"

    entry = (
        f"## {ts.strftime('%H:%M:%S')} — {project}"
        + (f" `{sid_short}`" if sid_short else "")
        + "\n\n"
        + prompt
        + "\n"
        + bucky_block
        + "\n---\n\n"
    )

    if not log_file.exists():
        header = (
            f"---\ntype: log\nstatus: active\ncreated: {ts.strftime('%Y-%m-%d')}\n"
            f"source: claudecode\ndepartment: [system]\n---\n\n"
            f"# Prompt Log — {ts.strftime('%Y-%m-%d')}\n\n"
        )
        log_file.write_text(header + entry, encoding="utf-8")
    else:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(entry)


if __name__ == "__main__":
    main()
