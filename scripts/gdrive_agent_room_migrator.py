#!/usr/bin/env python3
r"""
Google Drive Agent Room Migrator
G:\내 드라이브\JH-SHARED → ObsidianVault 단방향 이관

목적:
  - Google Drive의 구형 Agent Room 데이터를 ObsidianVault로 흡수
  - 이관 후 G: 드라이브는 읽기 전용 아카이브로 전환
  - Claude Code / Codex가 G: 드라이브를 불필요하게 탐색하지 못하게 방지

매핑:
  JH-SHARED/00_SYSTEM/      → ObsidianVault/00_System/gdrive-system/
  JH-SHARED/01_AGENT_ROOM/  → ObsidianVault/10_AgentBus/imported-agent-room/
  JH-SHARED/02_HANDOFF/     → ObsidianVault/10_AgentBus/handoffs/
  JH-SHARED/03_LOGS/        → ObsidianVault/05_Logs/gdrive-imported/
  JH-SHARED/04_DAILY_REPORTS/ → ObsidianVault/05_Logs/daily-reports-gdrive/
  JH-SHARED/05_TASK_LOCKS/  → ObsidianVault/10_AgentBus/task-locks-gdrive/
  JH-SHARED/06_TASK_LOGS/   → ObsidianVault/05_Logs/task-logs-gdrive/
  JH-SHARED/99_ARCHIVE/     → ObsidianVault/99_Archive/gdrive-archive/
  JH-SHARED/scripts/        → ObsidianVault/00_System/gdrive-scripts/
  JH-SHARED/.claude/        → ObsidianVault/00_System/gdrive-claude-config/
  JH-SHARED/*.json, *.md    → ObsidianVault/00_System/gdrive-root-files/
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
    "00_SYSTEM":        VAULT / "00_System" / "gdrive-system",
    "01_AGENT_ROOM":    VAULT / "10_AgentBus" / "imported-agent-room",
    "02_HANDOFF":       VAULT / "10_AgentBus" / "handoffs",
    "03_LOGS":          VAULT / "05_Logs" / "gdrive-imported",
    "04_DAILY_REPORTS": VAULT / "05_Logs" / "daily-reports-gdrive",
    "05_TASK_LOCKS":    VAULT / "10_AgentBus" / "task-locks-gdrive",
    "06_TASK_LOGS":     VAULT / "05_Logs" / "task-logs-gdrive",
    "99_ARCHIVE":       VAULT / "99_Archive" / "gdrive-archive",
    "scripts":          VAULT / "00_System" / "gdrive-scripts",
    ".claude":          VAULT / "00_System" / "gdrive-claude-config",
}

# 루트 파일 이관 대상 글로브 패턴 (폴더가 아닌 개별 파일)
ROOT_FILE_PATTERNS = ["*.json", "*.md"]
ROOT_FILES_DST = VAULT / "00_System" / "gdrive-root-files"

MIGRATION_LOG = VAULT / "10_AgentBus" / "gdrive-migration-log.json"
LOCK_FILE = _ROOT / ".gdrive-migration.lock"


def _iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _load_log() -> dict:
    if MIGRATION_LOG.exists():
        return json.loads(MIGRATION_LOG.read_text(encoding="utf-8"))
    return {"migrated": [], "skipped": [], "errors": [], "not_migrated": [], "last_run": None}


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

    if not dry_run:
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
            print(f"  [OK] {rel}")
        except Exception as e:
            log["errors"].append({"src": src_str, "error": str(e), "at": _iso()})
            errors += 1
            print(f"  [ERR] {rel}: {e}")

    return copied, skipped, errors


def migrate_root_files(
    src_root: Path,
    dst: Path,
    log: dict,
    patterns: list,
    dry_run: bool = False,
    force: bool = False,
) -> tuple[int, int, int]:
    """
    src_root 바로 아래의 파일(하위 폴더 제외)을 패턴에 맞춰 dst로 복사한다.
    루트 파일 전용 처리 (*.json, *.md 등).
    returns (copied, skipped, errors)
    """
    copied = skipped = errors = 0
    if not src_root.exists():
        return 0, 0, 0

    # 루트에 존재하는 파일만 (재귀 X)
    root_files_dict: dict = {}
    for pattern in patterns:
        for f in src_root.glob(pattern):
            if f.is_file():
                root_files_dict[str(f)] = f
    root_files = list(root_files_dict.values())

    if not root_files:
        return 0, 0, 0

    print(f"[gdrive-root-files] {len(root_files)}개 루트 파일 발견 → {dst.relative_to(VAULT)}")

    if not dry_run:
        dst.mkdir(parents=True, exist_ok=True)

    for item in root_files:
        dest_file = dst / item.name
        src_str = str(item)

        if not force and _already_migrated(log, src_str):
            skipped += 1
            continue

        if dry_run:
            print(f"  [DRY] {item.name} → {dest_file}")
            copied += 1
            continue

        try:
            shutil.copy2(item, dest_file)
            log["migrated"].append({"src": src_str, "dst": str(dest_file), "at": _iso()})
            copied += 1
            print(f"  [OK] {item.name}")
        except Exception as e:
            log["errors"].append({"src": src_str, "error": str(e), "at": _iso()})
            errors += 1
            print(f"  [ERR] {item.name}: {e}")

    return copied, skipped, errors


def check_unmigrated_items(src_root: Path) -> list:
    """
    src_root 하위에 존재하지만 MIGRATION_MAP 및 ROOT_FILE_PATTERNS에
    포함되지 않은 항목을 탐지하여 리포트용 목록을 반환한다.
    """
    if not src_root.exists():
        return []

    known_folders = set(MIGRATION_MAP.keys())
    known_ext = {p.lstrip("*.") for p in ROOT_FILE_PATTERNS}

    unmigrated = []
    for item in src_root.iterdir():
        if item.is_dir():
            if item.name not in known_folders:
                unmigrated.append(f"[폴더] {item.name}")
        else:
            if item.suffix.lstrip(".") not in known_ext:
                unmigrated.append(f"[파일] {item.name}")

    return unmigrated


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
    print(f"  [MARKER] 경계 마커 생성: {marker}")


def seed_manual_migration_log(log: dict) -> None:
    """
    이미 2026-05-25에 수동 이관한 항목을 로그에 시드한다.
    기존 완료 항목을 자동 migrator가 중복 복사하지 않도록 막는다.
    """
    migrated_srcs = {e["src"] for e in log.get("migrated", [])}
    for entry in MANUALLY_MIGRATED_FILES:
        if entry["src"] in migrated_srcs:
            continue
        log["migrated"].append({
            "src": entry["src"],
            "dst": entry["dst"],
            "at": entry["migrated_at"],
            "manual": True,
            "action": entry["action"],
        })
        migrated_srcs.add(entry["src"])


def run(dry_run: bool = False, force: bool = False) -> None:
    if LOCK_FILE.exists() and not force:
        print("[WARN] 마이그레이션이 이미 실행 중입니다 (.gdrive-migration.lock). --force로 덮어쓰기 가능.")
        return

    if not dry_run:
        LOCK_FILE.write_text(_iso())
    log = _load_log()
    if "not_migrated" not in log:
        log["not_migrated"] = []
    seed_manual_migration_log(log)
    log["last_run"] = _iso()

    total_copied = total_skipped = total_errors = 0

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Google Drive Agent Room 이관 시작")
    print(f"  소스: {GDRIVE_AGENT_ROOM}")
    print(f"  대상: {VAULT}\n")

    # ── 폴더 이관 ─────────────────────────────────────────────────────────────
    for folder_name, dst_path in MIGRATION_MAP.items():
        src_path = GDRIVE_AGENT_ROOM / folder_name
        print(f"[{folder_name}] → {dst_path.relative_to(VAULT)}")
        c, s, e = migrate_folder(src_path, dst_path, log, dry_run=dry_run, force=force)
        total_copied += c
        total_skipped += s
        total_errors += e

    # ── 루트 파일 이관 ────────────────────────────────────────────────────────
    c, s, e = migrate_root_files(
        GDRIVE_AGENT_ROOM, ROOT_FILES_DST, log, ROOT_FILE_PATTERNS,
        dry_run=dry_run, force=force,
    )
    total_copied += c
    total_skipped += s
    total_errors += e

    # ── 미이관 항목 탐지 및 로그 기록 ────────────────────────────────────────
    unmigrated = check_unmigrated_items(GDRIVE_AGENT_ROOM)
    if unmigrated:
        print(f"\n[REPORT] 미이관 항목 {len(unmigrated)}개:")
        for item in unmigrated:
            print(f"  - {item}")
        log["not_migrated"] = [
            {"item": item, "at": _iso()} for item in unmigrated
        ]
    else:
        log["not_migrated"] = []
        print("\n[REPORT] 미이관 항목 없음.")

    if not dry_run:
        create_vault_boundary_marker()
        _save_log(log)

    if not dry_run:
        LOCK_FILE.unlink(missing_ok=True)

    print(f"\n완료: 복사 {total_copied}개 / 스킵 {total_skipped}개 / 오류 {total_errors}개")
    if total_errors > 0:
        print(f"오류 로그: {MIGRATION_LOG}")
    if unmigrated:
        print(f"[WARN] 미이관 {len(unmigrated)}개 항목이 있습니다. MIGRATION_MAP 추가 검토 필요.")


# ============================================================
# MIGRATED_FILES — 수동 이관 완료 목록 (2026-05-25)
# Claude Code로 직접 Read/Write하여 이관한 파일들.
# gdrive_agent_room_migrator.py 자동 스캔 대상에서 중복 방지용.
# ============================================================
MANUALLY_MIGRATED_FILES = [
    # 00_SYSTEM → ObsidianVault/05_Frameworks/guides/
    {
        "src": r"G:\내 드라이브\JH-SHARED\00_SYSTEM\agent-onboarding.md",
        "dst": r"ObsidianVault\05_Frameworks\guides\agent-onboarding.md",
        "migrated_at": "2026-05-25",
        "action": "created",
    },
    {
        "src": r"G:\내 드라이브\JH-SHARED\00_SYSTEM\boris-phase1-report.md",
        "dst": r"ObsidianVault\05_Frameworks\guides\boris-phase1-report.md",
        "migrated_at": "2026-05-25",
        "action": "created",
    },
    {
        "src": r"G:\내 드라이브\JH-SHARED\00_SYSTEM\boris-phase2-plan.md",
        "dst": r"ObsidianVault\05_Frameworks\guides\boris-phase2-plan.md",
        "migrated_at": "2026-05-25",
        "action": "created",
    },
    {
        "src": r"G:\내 드라이브\JH-SHARED\00_SYSTEM\boris-phase2-report.md",
        "dst": r"ObsidianVault\05_Frameworks\guides\boris-phase2-report.md",
        "migrated_at": "2026-05-25",
        "action": "created",
    },
    {
        "src": r"G:\내 드라이브\JH-SHARED\00_SYSTEM\jh-system.md",
        "dst": r"ObsidianVault\05_Frameworks\guides\jh-system.md",
        "migrated_at": "2026-05-25",
        "action": "created",
    },
    {
        "src": r"G:\내 드라이브\JH-SHARED\00_SYSTEM\parallel-session-template.md",
        "dst": r"ObsidianVault\05_Frameworks\guides\parallel-session-template.md",
        "migrated_at": "2026-05-25",
        "action": "created",
    },
    {
        "src": r"G:\내 드라이브\JH-SHARED\00_SYSTEM\paths.md",
        "dst": r"ObsidianVault\05_Frameworks\guides\paths.md",
        "migrated_at": "2026-05-25",
        "action": "frontmatter_updated (already existed)",
    },
    {
        "src": r"G:\내 드라이브\JH-SHARED\00_SYSTEM\roles.md",
        "dst": r"ObsidianVault\05_Frameworks\guides\roles.md",
        "migrated_at": "2026-05-25",
        "action": "created",
    },
    {
        "src": r"G:\내 드라이브\JH-SHARED\00_SYSTEM\session-state.md",
        "dst": r"ObsidianVault\05_Frameworks\guides\session-state-gdrive.md",
        "migrated_at": "2026-05-25",
        "action": "created (snapshot mirror)",
    },
    {
        "src": r"G:\내 드라이브\JH-SHARED\00_SYSTEM\shared-protocol.md",
        "dst": r"ObsidianVault\05_Frameworks\guides\shared-protocol.md",
        "migrated_at": "2026-05-25",
        "action": "merged (gdrive version newer — added naming rules, additional prohibitions)",
    },
    {
        "src": r"G:\내 드라이브\JH-SHARED\00_SYSTEM\sync-protocol.md",
        "dst": r"ObsidianVault\05_Frameworks\guides\sync-protocol.md",
        "migrated_at": "2026-05-25",
        "action": "merged (gdrive version newer — full content with all sections)",
    },
    # 02_HANDOFF → ObsidianVault/00_System/archive/handoffs/
    {
        "src": r"G:\내 드라이브\JH-SHARED\02_HANDOFF\agent-startup-check.md",
        "dst": r"ObsidianVault\00_System\archive\handoffs\agent-startup-check.md",
        "migrated_at": "2026-05-25",
        "action": "created",
    },
    {
        "src": r"G:\내 드라이브\JH-SHARED\02_HANDOFF\claude-brief-agent-room-rehome.md",
        "dst": r"ObsidianVault\00_System\archive\handoffs\claude-brief-agent-room-rehome.md",
        "migrated_at": "2026-05-25",
        "action": "created",
    },
    {
        "src": r"G:\내 드라이브\JH-SHARED\02_HANDOFF\claude-obsidian-upgrade.md",
        "dst": r"ObsidianVault\00_System\archive\handoffs\claude-obsidian-upgrade.md",
        "migrated_at": "2026-05-25",
        "action": "created",
    },
    {
        "src": r"G:\내 드라이브\JH-SHARED\02_HANDOFF\claude-sync-context-guard.md",
        "dst": r"ObsidianVault\00_System\archive\handoffs\claude-sync-context-guard.md",
        "migrated_at": "2026-05-25",
        "action": "created",
    },
    {
        "src": r"G:\내 드라이브\JH-SHARED\02_HANDOFF\codex-sync-redesign-협의.md",
        "dst": r"ObsidianVault\00_System\archive\handoffs\codex-sync-redesign-협의.md",
        "migrated_at": "2026-05-25",
        "action": "created",
    },
    {
        "src": r"G:\내 드라이브\JH-SHARED\02_HANDOFF\handoff-20260502-claude-web.md",
        "dst": r"ObsidianVault\00_System\archive\handoffs\handoff-20260502-claude-web.md",
        "migrated_at": "2026-05-25",
        "action": "created",
    },
    {
        "src": r"G:\내 드라이브\JH-SHARED\02_HANDOFF\session-handoff-20260430.md",
        "dst": r"ObsidianVault\00_System\archive\handoffs\session-handoff-20260430.md",
        "migrated_at": "2026-05-25",
        "action": "created",
    },
    # 03_LOGS md 파일 → ObsidianVault/00_System/archive/
    {
        "src": r"G:\내 드라이브\JH-SHARED\03_LOGS\sync-log.md",
        "dst": r"ObsidianVault\00_System\archive\sync-log-gdrive.md",
        "migrated_at": "2026-05-25",
        "action": "created (snapshot)",
    },
    {
        "src": r"G:\내 드라이브\JH-SHARED\03_LOGS\sync-manifest.md",
        "dst": r"ObsidianVault\00_System\archive\sync-manifest-gdrive.md",
        "migrated_at": "2026-05-25",
        "action": "created (snapshot)",
    },
]
# ============================================================


if __name__ == "__main__":
    import sys
    dry = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    allowed = os.getenv("BUCKY_ALLOW_LEGACY_MIGRATION", "0").strip().lower() in {"1", "true", "yes", "on"}
    if not dry and not allowed:
        print(
            "[BLOCKED] Legacy Google Drive migration writes are disabled by default. "
            "Use --dry-run for inspection or set BUCKY_ALLOW_LEGACY_MIGRATION=1 from a Bucky-approved migration packet."
        )
        raise SystemExit(1)
    run(dry_run=dry, force=force)
