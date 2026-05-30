#!/usr/bin/env python3
"""
runbook_exporter.py — Card 7: 변경 시에만 런북 내보내기

BUCKY_OS_RUNBOOK.md 내용이 변경된 경우에만 exports/로 내보낸다.
변경이 없으면 내보내지 않고 "no change" 메시지를 출력한다.

사용법:
    python scripts/runbook_exporter.py             # 변경 감지 후 내보내기
    python scripts/runbook_exporter.py --force     # 강제 내보내기
    python scripts/runbook_exporter.py --status    # 현재 해시 상태만 확인
    python scripts/runbook_exporter.py --list      # 내보낸 파일 목록
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "ObsidianVault"
EXPORTS = ROOT / "exports"
HASH_STORE = ROOT / ".runbook_export_hash.json"

SOURCES = {
    "BUCKY_OS_RUNBOOK": VAULT / "00_System" / "BUCKY_OS_RUNBOOK.md",
    "ROUTING_RULES": VAULT / "00_System" / "ROUTING_RULES.md",
    "BUCKY_STATUS": VAULT / "00_System" / "BUCKY_STATUS.md",
}


def _sha256(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_store() -> dict[str, str]:
    if HASH_STORE.exists():
        try:
            return json.loads(HASH_STORE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_store(store: dict[str, str]) -> None:
    HASH_STORE.write_text(
        json.dumps(store, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def _export_file(key: str, src: Path) -> Path:
    EXPORTS.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    dest = EXPORTS / f"{key}_{date_str}.md"
    shutil.copy2(src, dest)
    return dest


def cmd_export(force: bool = False) -> int:
    store = _load_store()
    changed: list[str] = []
    skipped: list[str] = []
    exported: list[Path] = []

    for key, src in SOURCES.items():
        if not src.exists():
            print(f"  ⚠️  {key}: 파일 없음 ({src.relative_to(ROOT)})")
            continue

        current_hash = _sha256(src)
        prev_hash = store.get(key, "")

        if not force and current_hash == prev_hash:
            skipped.append(key)
            continue

        dest = _export_file(key, src)
        store[key] = current_hash
        changed.append(key)
        exported.append(dest)
        action = "강제" if force else "변경감지"
        print(f"  ✅  {key} [{action}] → {dest.relative_to(ROOT)}")

    if skipped:
        print(f"  ─  변경 없음 (내보내기 생략): {', '.join(skipped)}")

    _save_store(store)

    if not changed and not force:
        print("\n  변경된 런북 없음 — 내보내기 건너뜀")
    else:
        print(f"\n  내보내기 완료: {len(exported)}개 파일")
    return 0


def cmd_status() -> int:
    store = _load_store()
    print("\n── 런북 해시 상태 ──────────────────────────────────")
    for key, src in SOURCES.items():
        current = _sha256(src)
        stored = store.get(key, "(없음)")
        match = "✅ 동일" if current == stored else "🔄 변경됨"
        exists = "존재" if src.exists() else "❌ 없음"
        print(f"  {match}  {key:<22} [{exists}]  {current[:10]}...")
    print()
    return 0


def cmd_list() -> int:
    if not EXPORTS.exists():
        print("내보낸 파일 없음")
        return 0
    files = sorted(EXPORTS.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        print("내보낸 파일 없음")
        return 0
    print(f"\n── 내보낸 런북 목록 ({len(files)}개) ──────────────────")
    for f in files[:20]:
        size = f.stat().st_size
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        print(f"  {mtime}  {f.name:<45} {size:>6,}B")
    print()
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="강제 내보내기")
    ap.add_argument("--status", action="store_true", help="해시 상태만 확인")
    ap.add_argument("--list", action="store_true", help="내보낸 파일 목록")
    args = ap.parse_args()

    print()
    if args.status:
        sys.exit(cmd_status())
    elif args.list:
        sys.exit(cmd_list())
    else:
        sys.exit(cmd_export(force=args.force))


if __name__ == "__main__":
    main()
