#!/usr/bin/env python3
"""
Bucky 메모리 자동 압축(주차) 도구.

BUCKY_CONTEXT.md 의 '자동 학습된 사실 (Auto-Memory)' 섹션이 무한 누적되어
캐시 효율과 응답 속도가 저하되는 문제를 해결한다.

동작:
  1. 파일 크기가 threshold(기본 50KB)를 넘으면 발동(또는 --force).
  2. Auto-Memory 섹션의 entries(`- <emoji> [YYYY-MM-DD HH:MM] ...`) 파싱.
  3. 최근 keep_entries(기본 30) 개만 active 유지, 나머지는 09_Archive 로 주차.
  4. 활성 파일에는 주차 포인터(archive 경로) 1줄 추가.
  5. dry-run 시 변경 없이 어떤 일이 일어날지만 출력.

CLI 예:
  python -X utf8 scripts/bucky_memory_compactor.py --dry-run
  python -X utf8 scripts/bucky_memory_compactor.py --threshold-kb 50 --keep-entries 30
  python -X utf8 scripts/bucky_memory_compactor.py --force
"""

from __future__ import annotations

import argparse
import os
import re
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

_ROOT = Path(__file__).parent.parent
if load_dotenv:
    load_dotenv(_ROOT / ".env", encoding="utf-8-sig", override=True)

VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
CONTEXT_FILE = VAULT / "00_System" / "BUCKY_CONTEXT.md"
ARCHIVE_DIR = VAULT / "09_Archive" / "bucky-context-archive"

SECTION_HEADER = "## 🧠 자동 학습된 사실 (Auto-Memory)"
ARCHIVE_POINTER_PREFIX = "> 주차 이력:"

ENTRY_RE = re.compile(r"^- [^\[]*\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\] ")


def _split_section(content: str) -> tuple[str, list[str], str]:
    """본문을 (앞부분, auto-memory entries 리스트, 뒷부분)으로 분리.

    auto-memory section이 없으면 entries=[], 뒷부분=''.
    """
    idx = content.find(SECTION_HEADER)
    if idx == -1:
        return content, [], ""

    head = content[:idx]
    rest = content[idx + len(SECTION_HEADER):]

    next_section_match = re.search(r"\n(##\s)", rest)
    if next_section_match:
        body = rest[: next_section_match.start()]
        tail = rest[next_section_match.start():]
    else:
        body = rest
        tail = ""

    entries: list[str] = []
    other_lines: list[str] = []
    for line in body.splitlines():
        if ENTRY_RE.match(line):
            entries.append(line)
        else:
            other_lines.append(line)

    head_with_section = head + SECTION_HEADER + "\n" + "\n".join(other_lines).rstrip() + "\n"
    return head_with_section, entries, tail


def _archive_path(now: datetime) -> Path:
    return ARCHIVE_DIR / f"{now.strftime('%Y-%m-%d')}_auto_memory_archive.md"


def _write_archive(archive_file: Path, archived: list[str], now: datetime) -> None:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    if archive_file.exists():
        existing = archive_file.read_text(encoding="utf-8")
        block = f"\n\n## {now.strftime('%H:%M')} 추가 주차분 ({len(archived)}개)\n\n" + "\n".join(archived) + "\n"
        archive_file.write_text(existing.rstrip() + block, encoding="utf-8")
    else:
        header = (
            "---\n"
            "type: bucky-auto-memory-archive\n"
            f"created: {now.strftime('%Y-%m-%d %H:%M')}\n"
            f"source: ObsidianVault/00_System/BUCKY_CONTEXT.md\n"
            "tags:\n"
            "  - status/archive\n"
            "  - area/ai_automation\n"
            "---\n\n"
        )
        body = (
            f"# Bucky Auto-Memory Archive ({now.strftime('%Y-%m-%d')})\n\n"
            f"BUCKY_CONTEXT.md 자동 학습 섹션이 임계치를 넘어 주차된 entries 입니다. "
            f"읽기 전용 참고용이며 현재 운영 컨텍스트는 BUCKY_CONTEXT.md 본문을 사용하세요.\n\n"
            f"## 초기 주차분 ({len(archived)}개)\n\n" + "\n".join(archived) + "\n"
        )
        archive_file.write_text(header + body, encoding="utf-8")


def compact(
    context_file: Path = CONTEXT_FILE,
    threshold_kb: int = 50,
    keep_entries: int = 30,
    dry_run: bool = False,
    force: bool = False,
) -> dict:
    """BUCKY_CONTEXT.md 자동학습 섹션 주차.

    반환: {'triggered': bool, 'archived': int, 'kept': int, 'archive_path': str|None,
           'size_before': int, 'size_after': int}
    """
    if not context_file.exists():
        return {"triggered": False, "reason": "context file missing", "size_before": 0, "size_after": 0,
                "archived": 0, "kept": 0, "archive_path": None}

    raw = context_file.read_bytes()
    size_before = len(raw)
    threshold = threshold_kb * 1024

    if size_before < threshold and not force:
        return {"triggered": False, "reason": f"under threshold ({size_before}B < {threshold}B)",
                "size_before": size_before, "size_after": size_before,
                "archived": 0, "kept": 0, "archive_path": None}

    content = raw.decode("utf-8")
    head, entries, tail = _split_section(content)

    if not entries:
        return {"triggered": False, "reason": "no auto-memory entries found",
                "size_before": size_before, "size_after": size_before,
                "archived": 0, "kept": 0, "archive_path": None}

    if len(entries) <= keep_entries:
        return {"triggered": False, "reason": f"entries ({len(entries)}) <= keep_entries ({keep_entries})",
                "size_before": size_before, "size_after": size_before,
                "archived": 0, "kept": len(entries), "archive_path": None}

    archive_count = len(entries) - keep_entries
    to_archive = entries[:archive_count]
    to_keep = entries[archive_count:]

    now = datetime.now()
    archive_file = _archive_path(now)

    archive_rel = str(archive_file.relative_to(VAULT.parent)) if archive_file.is_absolute() else str(archive_file)

    pointer_line = f"{ARCHIVE_POINTER_PREFIX} `{archive_rel}` ({len(to_archive)}개 주차, {now.strftime('%Y-%m-%d %H:%M')})\n"

    head_lines = head.rstrip().splitlines()
    head_no_pointer = [ln for ln in head_lines if not ln.startswith(ARCHIVE_POINTER_PREFIX)]
    head_clean = "\n".join(head_no_pointer) + "\n"

    new_section = head_clean.rstrip() + "\n\n" + pointer_line + "\n" + "\n".join(to_keep) + "\n"
    if tail:
        new_section += tail

    size_after = len(new_section.encode("utf-8"))

    if dry_run:
        return {
            "triggered": True,
            "dry_run": True,
            "size_before": size_before,
            "size_after": size_after,
            "archived": len(to_archive),
            "kept": len(to_keep),
            "archive_path": str(archive_file),
            "preview_archive_first": to_archive[0] if to_archive else "",
            "preview_archive_last": to_archive[-1] if to_archive else "",
        }

    _write_archive(archive_file, to_archive, now)
    context_file.write_text(new_section, encoding="utf-8")

    return {
        "triggered": True,
        "dry_run": False,
        "size_before": size_before,
        "size_after": size_after,
        "archived": len(to_archive),
        "kept": len(to_keep),
        "archive_path": str(archive_file),
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Bucky BUCKY_CONTEXT.md auto-memory compactor")
    p.add_argument("--threshold-kb", type=int, default=50,
                   help="발동 임계 크기 (KB, 기본 50)")
    p.add_argument("--keep-entries", type=int, default=30,
                   help="active 유지 개수 (기본 30, 가장 최근 N개)")
    p.add_argument("--dry-run", action="store_true",
                   help="변경 없이 시뮬레이션만 수행")
    p.add_argument("--force", action="store_true",
                   help="임계치 미만이어도 강제 실행")
    p.add_argument("--context-file", default=str(CONTEXT_FILE),
                   help=f"대상 파일 (기본: {CONTEXT_FILE})")
    args = p.parse_args()

    result = compact(
        context_file=Path(args.context_file),
        threshold_kb=args.threshold_kb,
        keep_entries=args.keep_entries,
        dry_run=args.dry_run,
        force=args.force,
    )

    print(f"[compactor] triggered={result['triggered']} archived={result.get('archived', 0)} "
          f"kept={result.get('kept', 0)} size {result.get('size_before', 0)}B -> {result.get('size_after', 0)}B")
    if not result.get("triggered"):
        print(f"[compactor] reason: {result.get('reason', '')}")
    elif result.get("archive_path"):
        print(f"[compactor] archive: {result['archive_path']}")
        if result.get("dry_run"):
            print(f"[compactor] preview_first: {result.get('preview_archive_first', '')}")
            print(f"[compactor] preview_last:  {result.get('preview_archive_last', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
