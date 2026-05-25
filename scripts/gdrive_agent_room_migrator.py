#!/usr/bin/env python3
"""
Google Drive Agent Room Migrator
G:\내 드라이브\JH-SHARED → ObsidianVault 단방향 이관

목적:
  - Google Drive의 구형 Agent Room 데이터를 ObsidianVault로 흡수
  - 이관 후 G: 드라이브는 읽기 전용 아카이브로 전환
  - Claude Code / Codex가 G: 드라이브를 불필요하게 탐색하지 못하게 방지

매핑:
  JH-SHARED/01_AGENT_ROOM/  → ObsidianVault/10_AgentBus/imported-agent-room/
  JH-SHARED/02_HANDOFF/     → ObsidianVault/10_AgentBus/handoffs/
  JH-SHARED/03_LOGS/        → ObsidianVault/05_Logs/gdrive-imported/
  JH-SHARED/04_DAILY_REPORTS/ → ObsidianVault/05_Logs/daily-reports-gdrive/
  JH-SHARED/06_TASK_LOGS/   → ObsidianVault/05_Logs/task-logs-gdrive/
  JH-SHARED/00_SYSTEM/      → ObsidianVault/00_System/gdrive-system/
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env", encoding="utf-8", override=True)

VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
GDRIVE_AGENT_ROOM = Path(os.getenv("GDRIVE_AGENT_ROOM", r"G:\내 드라이브\JH-SHARED"))

MIGRATION_MAP = {
    "01_AGENT_ROOM": VAULT / "10_AgentBus" / "imported-agent-room",
    "02_HANDOFF": VAULT / "10_AgentBus" / "handoffs",
    "03_LOGS": VAULT / "05_Logs" / "gdrive-imported",
    "04_DAILY_REPORTS": VAULT / "05_Logs" / "daily-reports-gdrive",
    "06_TASK_LOGS": VAULT / "05_Logs" / "task-logs-gdrive",
    "00_SYSTEM": VAULT / "00_System" / "gdrive-system",
}

MIGRATION_LOG = VAULT / "10_AgentBus" / "gdrive-migration-log.json"
LOCK_FILE = _ROOT / ".gdrive-migration.lock"


def _iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _load_log() -> dict:
    if MIGRATION_LOG.exists():
        return json.loads(MIGRATION_LOG.read_text(encoding="utf-8"))
    return {"migrated": [], "skipped": [], "errors": [], "last_run": None}


def _save_log(log: dict) -> None:
    MIGRATION_LOG.parent.mkdir(parents=True, exist_ok=True)
    MIGRATION_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")


def _already_migrated(log: dict, src_path: str) -> bool:
    return src_path in {e["src"] for e in log.get("migrated", [])}


def migrate_folder(
    src: Path,
    dst: Path,
    log: dict,
    dry_run: bool = False,
    force: bool = False,
) -> tuple[int, int, int]:
    """src → dst 증분 복사. returns (copied, skipped, errors)"""
    copied = skipped = errors = 0
    if not src.exists():
        print(f"  [SKIP] 경로 없음: {src}")
        return 0, 0, 0

    dst.mkdir(parents=True, exist_ok=True)

    for item in src.rglob("*"):
        if item.is_dir():
            continue
        rel = item.relative_to(src)
        dest_file = dst / rel
        src_str = str(item)

        if not force and _already_migrated(log, src_str):
            skipped += 1
            continue

        if dry_run:
            print(f"  [DRY] {item} → {dest_file}")
            copied += 1
            continue

        try:
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest_file)
            log["migrated"].append({"src": src_str, "dst": str(dest_file), "at": _iso()})
            copied += 1
            print(f"  ✅ {rel}")
        except Exception as e:
            log["errors"].append({"src": src_str, "error": str(e), "at": _iso()})
            errors += 1
            print(f"  ❌ {rel}: {e}")

    return copied, skipped, errors


def create_vault_boundary_marker() -> None:
    """
    ObsidianVault 경계 표시 파일 생성.
    Claude Code / Codex가 이 파일을 보고 G: 드라이브 탐색을 중단하도록 유도.
    """
    marker = VAULT / "00_System" / "VAULT_BOUNDARY.md"
    marker.parent.mkdir(parents=True, exist_ok=True)
    content = """---
type: system
---
# Vault 경계 표시

이 파일이 있는 경로가 ObsidianVault의 루트입니다.

## 에이전트 준수 사항

- Claude Code / Codex는 **이 Vault 경계 밖** 경로를 임의 탐색하지 않는다.
- 특히 `G:\\내 드라이브\\JH-SHARED` (구 Agent Room)는 **읽기 금지** 경로.
- Google Drive 데이터 접근이 필요하면 `gdrive_agent_room_migrator.py`를 통해
  ObsidianVault 안으로 먼저 이관 후 처리한다.

## 허용 경로 (Claude Code 작업 대상)

- `G:\\내 드라이브\\obsidian-agent-brain-system\\` (이 저장소)
- `ObsidianVault\\` (Vault 루트)
- `scripts\\` (스크립트)
"""
    marker.write_text(content, encoding="utf-8")
    print(f"  📌 경계 마커 생성: {marker}")


def run(dry_run: bool = False, force: bool = False) -> None:
    if LOCK_FILE.exists() and not force:
        print("⚠️ 마이그레이션이 이미 실행 중입니다 (.gdrive-migration.lock). --force로 덮어쓰기 가능.")
        return

    LOCK_FILE.write_text(_iso())
    log = _load_log()
    log["last_run"] = _iso()

    total_copied = total_skipped = total_errors = 0

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Google Drive Agent Room 이관 시작")
    print(f"  소스: {GDRIVE_AGENT_ROOM}")
    print(f"  대상: {VAULT}\n")

    for folder_name, dst_path in MIGRATION_MAP.items():
        src_path = GDRIVE_AGENT_ROOM / folder_name
        print(f"[{folder_name}] → {dst_path.relative_to(VAULT)}")
        c, s, e = migrate_folder(src_path, dst_path, log, dry_run=dry_run, force=force)
        total_copied += c
        total_skipped += s
        total_errors += e

    if not dry_run:
        create_vault_boundary_marker()
        _save_log(log)

    LOCK_FILE.unlink(missing_ok=True)

    print(f"\n완료: 복사 {total_copied}개 / 스킵 {total_skipped}개 / 오류 {total_errors}개")
    if total_errors > 0:
        print(f"오류 로그: {MIGRATION_LOG}")


if __name__ == "__main__":
    import sys
    dry = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    run(dry_run=dry, force=force)
