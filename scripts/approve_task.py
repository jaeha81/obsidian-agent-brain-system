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
import json
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
_JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


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


def _execute_approved_wishket_request(path: Path) -> str:
    content = path.read_text(encoding="utf-8", errors="replace")
    fm, body = _parse(content)
    if fm.get("type") != "wishket_development_request":
        return ""
    match = _JSON_BLOCK_RE.search(body)
    if not match:
        raise ValueError("wishket payload JSON block not found")
    from wishket_development_request import execute_local_creation, normalize_payload

    payload = normalize_payload(json.loads(match.group(1)))
    result = execute_local_creation(payload)
    return result["created"]


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
    try:
        execution_result = _execute_approved_wishket_request(path)
    except Exception as e:
        print(f"approval execution failed: {e}")
        sys.exit(1)
    _write_fm(path, {
        "status": "pending",
        "requires_approval": False,
        "approved_at": _iso(),
        "approval_note": "approved via approve_task.py",
        "execution_result": execution_result,
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


def list_pending_dicts() -> list:
    """pending_approval/ 대기 태스크를 dict 목록으로 반환 (모듈 임포트용)."""
    PENDING.mkdir(parents=True, exist_ok=True)
    tasks = sorted(PENDING.glob("*.md"))
    result = []
    for idx, t in enumerate(tasks, 1):
        try:
            content = t.read_text(encoding="utf-8", errors="replace")
        except Exception:
            content = ""
        fm, _ = _parse(content)
        result.append({
            "idx": idx,
            "name": t.name,
            "stem": t.stem,
            "type": fm.get("type", "unknown"),
            "queued_at": fm.get("queued_at", ""),
            "approval_note": fm.get("approval_note", "")[:80],
        })
    return result


def _resolve_key(key: str) -> Path | None:
    """숫자 인덱스 또는 부분 이름으로 pending_approval/ 파일 찾기."""
    tasks = sorted(PENDING.glob("*.md"))
    if not tasks:
        return None
    # 숫자 → 인덱스
    if key.isdigit():
        idx = int(key)
        if 1 <= idx <= len(tasks):
            return tasks[idx - 1]
        return None
    # 정확한 파일명
    exact = PENDING / key
    if not exact.suffix:
        exact = PENDING / (key + ".md")
    if exact.exists():
        return exact
    # 부분 일치
    key_lower = key.lower()
    matches = [t for t in tasks if key_lower in t.stem.lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        return None  # 모호함 — 호출자가 처리
    return None


def approve_by_key(key: str) -> dict:
    """key(인덱스·부분명)로 태스크 승인. 반환: {ok, name, error}."""
    PENDING.mkdir(parents=True, exist_ok=True)
    tasks = sorted(PENDING.glob("*.md"))
    # 모호함 감지
    if key.isdigit():
        path = _resolve_key(key)
    else:
        key_lower = key.lower()
        matches = [t for t in tasks if key_lower in t.stem.lower()]
        if len(matches) > 1:
            return {"ok": False, "name": "", "error": f"모호한 키 '{key}' — {len(matches)}개 매칭"}
        path = matches[0] if matches else _resolve_key(key)

    if not path or not path.exists():
        return {"ok": False, "name": key, "error": f"파일 없음: {key}"}

    INBOX.mkdir(parents=True, exist_ok=True)
    try:
        execution_result = _execute_approved_wishket_request(path)
    except Exception as e:
        return {"ok": False, "name": path.name, "error": f"approval execution failed: {e}"}
    _write_fm(path, {
        "status": "pending",
        "requires_approval": False,
        "approved_at": _iso(),
        "approval_note": "approved via Discord !approve",
        "execution_result": execution_result,
    })
    dest = INBOX / path.name
    path.rename(dest)
    return {"ok": True, "name": path.name, "error": ""}


def reject_by_key(key: str, reason: str = "") -> dict:
    """key(인덱스·부분명)로 태스크 거절. 반환: {ok, name, error}."""
    PENDING.mkdir(parents=True, exist_ok=True)
    tasks = sorted(PENDING.glob("*.md"))
    if key.isdigit():
        path = _resolve_key(key)
    else:
        key_lower = key.lower()
        matches = [t for t in tasks if key_lower in t.stem.lower()]
        if len(matches) > 1:
            return {"ok": False, "name": "", "error": f"모호한 키 '{key}' — {len(matches)}개 매칭"}
        path = matches[0] if matches else _resolve_key(key)

    if not path or not path.exists():
        return {"ok": False, "name": key, "error": f"파일 없음: {key}"}

    FAILED.mkdir(parents=True, exist_ok=True)
    _write_fm(path, {
        "status": "rejected",
        "rejected_at": _iso(),
        "rejection_reason": reason or "rejected via Discord !reject",
    })
    dest = FAILED / path.name
    path.rename(dest)
    return {"ok": True, "name": path.name, "error": ""}


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
