#!/usr/bin/env python3
"""JH 발화 DB export — conv_history(role=user)를 promptlog에 증분 기록.

실행:
    python -X utf8 scripts/promptlog_export.py [--date YYYY-MM-DD]

--date 미지정 시 오늘 날짜.
체크포인트: PROMPTLOG_DIR/.export_checkpoint.json (마지막 처리 row id 저장).
중복: ts+hash 기반 스킵 (promptlog_hook.py와 동일 포맷).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
VAULT = ROOT / "ObsidianVault"
PROMPTLOG_DIR = VAULT / "09_Knowledge_Capture" / "promptlog"
CHECKPOINT_FILE = PROMPTLOG_DIR / ".export_checkpoint.json"

# 정본 DB: 10_AgentBus/tasks/bucky_memory.db (env 오버라이드 허용)
DEFAULT_DB = VAULT / "10_AgentBus" / "tasks" / "bucky_memory.db"

_REDACT_PATTERNS: list[re.Pattern] = [
    re.compile(r"(sk-[A-Za-z0-9_\-]{20,})", re.IGNORECASE),
    re.compile(r"(xai-[A-Za-z0-9_\-]{20,})", re.IGNORECASE),
    re.compile(r"(AIza[A-Za-z0-9_\-]{35,})", re.IGNORECASE),
    re.compile(r"(Bearer\s+[A-Za-z0-9_\-\.]{20,})", re.IGNORECASE),
    re.compile(r"(?:api[_\-]?key|token|secret)[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9_\-\.]{16,})", re.IGNORECASE),
    re.compile(r"\b(\d{6}[-\s]\d{7})\b"),
    re.compile(r"\b(\d{4}[\s\-]\d{4}[\s\-]\d{4}[\s\-]\d{4})\b"),
]


def _redact(text: str) -> str:
    for pat in _REDACT_PATTERNS:
        text = pat.sub("[REDACTED]", text)
    return text


def _load_checkpoint() -> int:
    if CHECKPOINT_FILE.exists():
        try:
            return json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8")).get("last_id", 0)
        except Exception:
            pass
    return 0


def _save_checkpoint(last_id: int) -> None:
    CHECKPOINT_FILE.write_text(json.dumps({"last_id": last_id, "updated": datetime.now().isoformat(timespec="seconds")}), encoding="utf-8")


def _load_seen(log_path: Path) -> set[str]:
    seen: set[str] = set()
    if not log_path.exists():
        return seen
    for line in log_path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"<!--\s*dedup:\s*(\S+)\s*-->", line)
        if m:
            seen.add(m.group(1))
    return seen


def _ensure_frontmatter(log_path: Path, date_str: str) -> None:
    if log_path.exists():
        return
    PROMPTLOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        f"---\ntype: promptlog\ndate: {date_str}\nstatus: active\n---\n\n"
        f"# JH Promptlog — {date_str}\n\n",
        encoding="utf-8",
    )


def export(target_date: str, db_path: Path) -> dict:
    if not db_path.exists():
        return {"error": f"DB not found: {db_path}", "exported": 0, "skipped": 0}

    last_id = _load_checkpoint()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # ts 컬럼명은 bucky_memory.db 실측 기준 (memory-evolution-direction.md §3 P0 확인)
    rows = conn.execute(
        """
        SELECT id, ts, content
        FROM conv_history
        WHERE role = 'user'
          AND id > ?
          AND date(ts) = ?
        ORDER BY id ASC
        """,
        (last_id, target_date),
    ).fetchall()
    conn.close()

    log_path = PROMPTLOG_DIR / f"{target_date}.md"
    seen = _load_seen(log_path)

    exported = 0
    skipped = 0
    new_last_id = last_id

    for row in rows:
        row_id = row["id"]
        ts_raw = row["ts"] or ""
        content = (row["content"] or "").strip()
        if not content:
            new_last_id = max(new_last_id, row_id)
            continue

        # ts 파싱 — ISO 형식 "2026-06-13T14:30:00" 또는 "2026-06-13 14:30:00"
        try:
            ts_dt = datetime.fromisoformat(ts_raw.replace(" ", "T"))
            ts_str = ts_dt.strftime("%H:%M:%S")
        except Exception:
            ts_str = "00:00:00"

        prompt_redacted = _redact(content)
        prompt_hash = hashlib.sha1(prompt_redacted.encode("utf-8")).hexdigest()[:8]
        dedup_key = f"{ts_str}:{prompt_hash}"

        if dedup_key in seen:
            skipped += 1
            new_last_id = max(new_last_id, row_id)
            continue

        _ensure_frontmatter(log_path, target_date)
        entry = (
            f"<!-- dedup: {dedup_key} -->\n"
            f"## {ts_str} [discord]\n\n"
            f"{prompt_redacted}\n\n"
        )
        with log_path.open("a", encoding="utf-8") as f:
            f.write(entry)

        seen.add(dedup_key)
        exported += 1
        new_last_id = max(new_last_id, row_id)

    if new_last_id > last_id:
        _save_checkpoint(new_last_id)

    return {"date": target_date, "exported": exported, "skipped": skipped, "last_id": new_last_id}


def main() -> None:
    parser = argparse.ArgumentParser(description="Export JH prompts from conv_history to promptlog.")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="Target date (YYYY-MM-DD)")
    parser.add_argument("--db", default=None, help="Override DB path")
    args = parser.parse_args()

    db_path = Path(args.db) if args.db else Path(os.environ.get("BUCKY_MEMORY_DB_PATH", str(DEFAULT_DB)))
    result = export(args.date, db_path)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
