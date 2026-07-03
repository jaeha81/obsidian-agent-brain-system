#!/usr/bin/env python3
"""Sync repo CLAUDE.md to the generated global Claude Code target.

Usage:
  python scripts/sync_claude_instructions.py
  python scripts/sync_claude_instructions.py --check
  python scripts/sync_claude_instructions.py --dry-run

AgentBus can call this for type=claude_sync messages. The instruction source is
the repository-level CLAUDE.md managed by Bucky, not the generated global file.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import shutil
import sys
from datetime import datetime
from pathlib import Path


if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf-8-sig"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf-8-sig"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
SOURCE = ROOT / "CLAUDE.md"
DEST = Path.home() / ".claude" / "CLAUDE.md"
BACKUP_DIR = Path.home() / ".claude" / "backups"

_OBSIDIAN_NOTICE = "> **[Obsidian 관리 파일]**"


def _managed_header() -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    return (
        f"<!-- AUTO-GENERATED {ts} from repo CLAUDE.md. "
        "Edit the repo source, not this generated target. -->\n"
    )


def _strip_obsidian_notice(text: str) -> str:
    """Remove Obsidian-only notice lines before global sync."""
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    skip_next_blank = False
    for line in lines:
        if _OBSIDIAN_NOTICE in line:
            skip_next_blank = True
            continue
        if skip_next_blank and line.strip() == "":
            skip_next_blank = False
            continue
        skip_next_blank = False
        out.append(line)
    return "".join(out)


def _md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def _strip_managed_header(text: str) -> str:
    lines = text.splitlines(keepends=True)
    if lines and lines[0].startswith("<!-- AUTO-GENERATED"):
        return "".join(lines[1:])
    return text


def _backup(path: Path) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"CLAUDE_{ts}.md"
    shutil.copy2(path, dest)
    return dest


def sync(dry_run: bool = False, check_only: bool = False) -> int:
    if not SOURCE.exists():
        print(f"[ERROR] source file missing: {SOURCE}", file=sys.stderr)
        return 1

    raw = SOURCE.read_text(encoding="utf-8")
    new_content = _managed_header() + _strip_obsidian_notice(raw)

    if DEST.exists():
        existing = DEST.read_text(encoding="utf-8")
        if _md5(_strip_managed_header(existing)) == _md5(_strip_managed_header(new_content)):
            print("[OK] global CLAUDE.md is current")
            return 0
        if check_only:
            print("[INFO] global CLAUDE.md differs; sync required")
            return 2

    if dry_run:
        print(f"[DRY-RUN] {SOURCE} -> {DEST}")
        print("--- preview first 20 lines ---")
        for line in new_content.splitlines()[:20]:
            print(line)
        return 0

    if DEST.exists():
        bak = _backup(DEST)
        print(f"[Backup] {bak}")

    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(new_content, encoding="utf-8")
    print(f"[OK] synced: {SOURCE.name} -> {DEST}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Sync repo CLAUDE.md to generated global Claude Code target")
    ap.add_argument("--check", action="store_true", help="check whether sync is needed")
    ap.add_argument("--dry-run", action="store_true", help="preview without writing")
    args = ap.parse_args()
    sys.exit(sync(dry_run=args.dry_run, check_only=args.check))
