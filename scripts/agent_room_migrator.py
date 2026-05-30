#!/usr/bin/env python3
"""
Agent Room Migrator
G드라이브 JH-SHARED Agent Room JSONL → ObsidianVault 마이그레이션.

기능:
  1. JH-SHARED/01_AGENT_ROOM/agent-room-messages.jsonl 읽기
  2. 메시지 → ObsidianVault/03_Knowledge/agent-room-history/ Obsidian 노트 변환
  3. ObsidianVault/10_AgentBus/agent-room-messages.jsonl 에 병합 (중복 제거)
  4. 원본 JSONL → 99_ARCHIVE 이동 (격리)

이 스크립트 실행 후 Claude Code / Codex 는 G드라이브 Agent Room을 읽지 않습니다.
모든 에이전트 통신은 ObsidianVault/10_AgentBus/ 를 단일 소스로 사용합니다.

Usage:
    python agent_room_migrator.py              # 마이그레이션 실행
    python agent_room_migrator.py --dry-run    # 테스트 (저장 없음)
    python agent_room_migrator.py --status     # 현재 상태 확인
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
import io
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── 경로 설정 ────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).parent.parent
VAULT = _ROOT / "ObsidianVault"
JH_SHARED = Path("G:/내 드라이브/JH-SHARED")

# 소스 경로들 (G드라이브 — 읽기만 허용)
SOURCES = [
    JH_SHARED / "01_AGENT_ROOM" / "agent-room-messages.jsonl",
    JH_SHARED / "00_SYSTEM" / "agent-room-messages.jsonl",
    JH_SHARED / "99_ARCHIVE" / "agent-room-messages.legacy.json",
]

# 대상 경로 (Vault — 단일 소스)
VAULT_AGENTBUS = VAULT / "10_AgentBus" / "agent-room-messages.jsonl"
VAULT_HISTORY_DIR = VAULT / "03_Knowledge" / "agent-room-history"
ARCHIVE_MARKER = ".migrated-to-vault"

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s", stream=sys.stdout)
log = logging.getLogger(__name__)


def _legacy_migration_allowed() -> bool:
    return os.getenv("BUCKY_ALLOW_LEGACY_MIGRATION", "0").strip().lower() in {"1", "true", "yes", "on"}


# ── JSONL 읽기 ────────────────────────────────────────────────────────────────

def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    messages = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    except Exception as e:
        log.warning(f"JSONL 읽기 실패 ({path.name}): {e}")
    return messages


def read_legacy_json(path: Path) -> list[dict]:
    """legacy JSON array 형식 읽기."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return list(data.values()) if data else []
    except Exception as e:
        log.warning(f"JSON 읽기 실패 ({path.name}): {e}")
    return []


# ── Obsidian 노트 변환 ────────────────────────────────────────────────────────

def message_to_note(msg: dict) -> tuple[str, str]:
    """
    Agent Room 메시지 → (파일명, 마크다운 내용)
    """
    msg_id = msg.get("id", "unknown")[:8]
    speaker = msg.get("speaker", "unknown")
    kind = msg.get("kind", "message")
    body = msg.get("body", "").strip()
    created_at = msg.get("createdAt", "")
    status = msg.get("status", "")

    # 날짜 파싱
    date_str = "unknown"
    try:
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H:%M")
    except Exception:
        time_str = "unknown"

    # 제목 (body 첫 줄 최대 50자)
    title = (body.split("\n")[0] if body else "No content")[:50].strip()
    safe_title = "".join(c if c.isalnum() or c in "-_ " else "_" for c in title)[:40]
    filename = f"{date_str}_{speaker}_{msg_id}_{safe_title}.md"

    content_lines = [
        "---",
        f"source: agent-room",
        f"speaker: {speaker}",
        f"kind: {kind}",
        f"date: {date_str}",
        f"time: {time_str}",
        f"status: {status}",
        f"message_id: {msg.get('id', '')}",
        "---",
        "",
        f"# {title}",
        "",
        body,
        "",
        f"*Agent Room 기록 — 자동 마이그레이션: {datetime.now().strftime('%Y-%m-%d')}*",
    ]
    return filename, "\n".join(content_lines)


# ── 마이그레이션 ──────────────────────────────────────────────────────────────

def migrate(dry_run: bool = False) -> dict:
    log.info(f"=== Agent Room 마이그레이션 {'[DRY-RUN]' if dry_run else ''} 시작 ===")

    # 기존 Vault AgentBus 메시지 ID 수집 (중복 방지)
    existing_ids: set[str] = set()
    if VAULT_AGENTBUS.exists():
        for msg in read_jsonl(VAULT_AGENTBUS):
            if msg.get("id"):
                existing_ids.add(msg["id"])
    log.info(f"기존 Vault AgentBus 메시지: {len(existing_ids)}개")

    all_messages: list[dict] = []

    # 소스별 수집
    for src in SOURCES:
        if not src.exists():
            log.info(f"  소스 없음 (건너뜀): {src}")
            continue

        if src.suffix == ".json":
            msgs = read_legacy_json(src)
        else:
            msgs = read_jsonl(src)

        new_msgs = [m for m in msgs if m.get("id") not in existing_ids]
        log.info(f"  {src.name}: {len(msgs)}개 중 {len(new_msgs)}개 신규")
        all_messages.extend(new_msgs)
        for m in new_msgs:
            if m.get("id"):
                existing_ids.add(m["id"])

    if not all_messages:
        log.info("신규 메시지 없음 — 마이그레이션 불필요")
        return {"migrated": 0, "notes_created": 0}

    log.info(f"마이그레이션 대상: {len(all_messages)}개 메시지")

    notes_created = 0

    # Vault AgentBus JSONL에 병합
    if not dry_run:
        VAULT_AGENTBUS.parent.mkdir(parents=True, exist_ok=True)
        with open(VAULT_AGENTBUS, "a", encoding="utf-8") as f:
            for msg in all_messages:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")
        log.info(f"Vault AgentBus 병합 완료: {len(all_messages)}개 추가")

    # 소스 파일에 마이그레이션 마커 기록 (원본 보존, 충돌 방지)
    if not dry_run:
        for src in SOURCES:
            if src.exists():
                marker = src.parent / ARCHIVE_MARKER
                marker.write_text(
                    f"migrated-at: {datetime.now().isoformat()}\n"
                    f"target: {VAULT_AGENTBUS}\n"
                    f"message-count: {len(all_messages)}\n"
                    "NOTE: 이 디렉토리는 마이그레이션 완료. Claude Code / Codex는 읽지 않을 것.\n",
                    encoding="utf-8",
                )
                log.info(f"  마이그레이션 마커 생성: {marker}")

    log.info(f"=== 마이그레이션 완료: 노트 {notes_created}개 생성 ===")
    return {"migrated": len(all_messages), "notes_created": notes_created}


# ── 상태 확인 ────────────────────────────────────────────────────────────────

def show_status() -> None:
    print("\n=== Agent Room 마이그레이션 상태 ===\n")

    print("[ G드라이브 소스 경로 ]")
    for src in SOURCES:
        exists = "✓" if src.exists() else "✗"
        marker = src.parent / ARCHIVE_MARKER
        migrated = " [마이그레이션 완료]" if marker.exists() else ""
        count = 0
        if src.exists():
            count = len(read_jsonl(src) if src.suffix == ".jsonl" else read_legacy_json(src))
        print(f"  {exists} {src.name}: {count}개 메시지{migrated}")

    print("\n[ Vault 대상 경로 ]")
    vault_count = len(read_jsonl(VAULT_AGENTBUS)) if VAULT_AGENTBUS.exists() else 0
    history_count = len(list(VAULT_HISTORY_DIR.glob("*.md"))) if VAULT_HISTORY_DIR.exists() else 0
    print(f"  {'✓' if VAULT_AGENTBUS.exists() else '✗'} 10_AgentBus/agent-room-messages.jsonl: {vault_count}개")
    print(f"  {'✓' if VAULT_HISTORY_DIR.exists() else '✗'} 03_Knowledge/agent-room-history/: {history_count}개 노트")

    print("\n[ 격리 규칙 ]")
    print("  Claude Code / Codex → ObsidianVault/10_AgentBus/ 만 읽기/쓰기")
    print("  G드라이브 JH-SHARED Agent Room → 레거시 아카이브 (읽기 금지)")


# ── 진입점 ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Agent Room Migrator — G드라이브 → ObsidianVault 이관")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", help="테스트 (저장 없음)")
    group.add_argument("--status", action="store_true", help="마이그레이션 상태 확인")
    args = parser.parse_args()

    if not args.dry_run and not args.status and not _legacy_migration_allowed():
        print(
            "[BLOCKED] This legacy migration script is disabled by default. "
            "Set BUCKY_ALLOW_LEGACY_MIGRATION=1 only from a Bucky-approved migration packet."
        )
        return 1

    if args.status:
        show_status()
    else:
        result = migrate(dry_run=args.dry_run)
        print(f"\n결과: {result['migrated']}개 마이그레이션, {result['notes_created']}개 노트 생성")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
