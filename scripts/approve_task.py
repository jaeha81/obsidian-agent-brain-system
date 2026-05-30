#!/usr/bin/env python3
"""
approve_task.py — pending_approval/ 대기 태스크 관리 CLI

사용법:
    python scripts/approve_task.py list             # 대기 중인 태스크 목록
    python scripts/approve_task.py approve <name>   # 태스크 승인 → inbox/ 복귀
    python scripts/approve_task.py reject <name>    # 태스크 거절 → failed/
    python scripts/approve_task.py show <name>      # 태스크 내용 출력
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
VAULT = Path(os.getenv("VAULT_PATH", str(ROOT / "ObsidianVault")))
PENDING = VAULT / "10_AgentBus" / "pending_approval"
INBOX = VAULT / "10_AgentBus" / "inbox"
FAILED = VAULT / "10_AgentBus" / "failed"

_FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def _iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _parse(text: str) -> tuple[dict, str]:
    m = _FM_RE.match(text)
    if m:
        try:
            return yaml.safe_load(m.group(1)) or {}, text[m.end():]
        except yaml.YAMLError:
            return {}, text
    return {}, text


def _write_fm(filepath: Path, updates: dict) -> None:
    content = filepath.read_text(encoding="utf-8")
    fm, body = _parse(content)
    fm.update(updates)
    filepath.write_text(
        f"---\n{yaml.dump(fm, allow_unicode=True, default_flow_style=False)}---\n{body}",
        encoding="utf-8",
    )


def cmd_list() -> None:
    PENDING.mkdir(parents=True, exist_ok=True)
    tasks = sorted(PENDING.glob("*.md"))
    if not tasks:
        print("대기 중인 승인 태스크 없음.")
        return
    print(f"대기 중인 승인 태스크 ({len(tasks)}개):\n")
    for t in tasks:
        content = t.read_text(encoding="utf-8", errors="replace")
        fm, body = _parse(content)
        task_type = fm.get("type", "unknown")
        queued = fm.get("queued_at", "-")
        note = fm.get("approval_note", "")[:60]
        print(f"  {t.name}")
        print(f"    type={task_type}  queued={queued}")
        if note:
            print(f"    {note}")
        print()


def cmd_show(name: str) -> None:
    path = PENDING / name
    if not path.suffix:
        path = PENDING / (name + ".md")
    if not path.exists():
        print(f"파일 없음: {path}")
        sys.exit(1)
    print(path.read_text(encoding="utf-8", errors="replace"))


def cmd_approve(name: str) -> None:
    path = PENDING / name
    if not path.suffix:
        path = PENDING / (name + ".md")
    if not path.exists():
        print(f"파일 없음: {path}")
        sys.exit(1)
    INBOX.mkdir(parents=True, exist_ok=True)
    _write_fm(path, {
        "status": "pending",
        "requires_approval": False,
        "approved_at": _iso(),
        "approval_note": "approved via approve_task.py",
    })
    dest = INBOX / path.name
    path.rename(dest)
    print(f"✅ 승인 완료: {path.name} → inbox/")


def cmd_reject(name: str) -> None:
    path = PENDING / name
    if not path.suffix:
        path = PENDING / (name + ".md")
    if not path.exists():
        print(f"파일 없음: {path}")
        sys.exit(1)
    FAILED.mkdir(parents=True, exist_ok=True)
    _write_fm(path, {
        "status": "rejected",
        "rejected_at": _iso(),
    })
    dest = FAILED / path.name
    path.rename(dest)
    print(f"❌ 거절 완료: {path.name} → failed/")


def main() -> int:
    ap = argparse.ArgumentParser(description="pending_approval 태스크 관리")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("list", help="대기 목록")
    show_p = sub.add_parser("show", help="태스크 내용 출력")
    show_p.add_argument("name")
    approve_p = sub.add_parser("approve", help="승인 → inbox 복귀")
    approve_p.add_argument("name")
    reject_p = sub.add_parser("reject", help="거절 → failed")
    reject_p.add_argument("name")

    args = ap.parse_args()
    if args.cmd == "list" or args.cmd is None:
        cmd_list()
    elif args.cmd == "show":
        cmd_show(args.name)
    elif args.cmd == "approve":
        cmd_approve(args.name)
    elif args.cmd == "reject":
        cmd_reject(args.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
