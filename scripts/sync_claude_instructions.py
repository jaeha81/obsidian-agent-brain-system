#!/usr/bin/env python3
"""
sync_claude_instructions.py
Obsidian CLAUDE_MASTER.md → ~/.claude/CLAUDE.md 동기화.

사용법:
  python3 scripts/sync_claude_instructions.py           # 동기화 실행
  python3 scripts/sync_claude_instructions.py --check   # 변경 여부만 확인
  python3 scripts/sync_claude_instructions.py --dry-run # 미리보기 (쓰기 안 함)

AgentBus에서도 호출됨: type=claude_sync 메시지 수신 시.
"""

import argparse
import hashlib
import io
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Windows cp949 터미널에서도 한글·특수문자 출력
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf-8-sig"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf-8-sig"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

VAULT_ROOT = Path(__file__).parent.parent / "ObsidianVault"
SOURCE = VAULT_ROOT / "05_Frameworks" / "guides" / "CLAUDE_MASTER.md"
DEST = Path.home() / ".claude" / "CLAUDE.md"
BACKUP_DIR = Path.home() / ".claude" / "backups"

_MANAGED_HEADER = "<!-- AUTO-GENERATED from Obsidian CLAUDE_MASTER.md — edit there, not here -->\n"
_OBSIDIAN_NOTICE = "> **[Obsidian 관리 파일]**"


def _strip_obsidian_notice(text: str) -> str:
    """CLAUDE_MASTER.md 상단의 Obsidian 전용 안내 줄을 제거한다."""
    lines = text.splitlines(keepends=True)
    out = []
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


def _backup(path: Path) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"CLAUDE_{ts}.md"
    shutil.copy2(path, dest)
    return dest


def sync(dry_run: bool = False, check_only: bool = False) -> int:
    if not SOURCE.exists():
        print(f"[ERROR] 소스 파일 없음: {SOURCE}", file=sys.stderr)
        return 1

    raw = SOURCE.read_text(encoding="utf-8")
    new_content = _managed_header() + _strip_obsidian_notice(raw)

    if DEST.exists():
        existing = DEST.read_text(encoding="utf-8")
        if _md5(existing) == _md5(new_content):
            print("[OK] CLAUDE.md 이미 최신입니다.")
            return 0
        if check_only:
            print("[INFO] CLAUDE.md 변경 감지됨 — sync 필요.")
            return 2

    if dry_run:
        print(f"[DRY-RUN] {SOURCE} → {DEST}")
        print("--- 미리보기 (첫 20줄) ---")
        for line in new_content.splitlines()[:20]:
            print(line)
        return 0

    if DEST.exists():
        bak = _backup(DEST)
        print(f"[Backup] {bak}")

    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(new_content, encoding="utf-8")
    print(f"[OK] 동기화 완료: {SOURCE.name} → {DEST}")
    return 0


def _managed_header() -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    return (
        f"<!-- AUTO-GENERATED {ts}"
        f" — 수정은 Obsidian의 CLAUDE_MASTER.md 에서 하세요 -->\n"
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Obsidian CLAUDE_MASTER.md → CLAUDE.md 동기화")
    ap.add_argument("--check", action="store_true", help="변경 여부 확인만 (쓰기 안 함)")
    ap.add_argument("--dry-run", action="store_true", help="실제 쓰기 없이 미리보기")
    args = ap.parse_args()
    sys.exit(sync(dry_run=args.dry_run, check_only=args.check))
