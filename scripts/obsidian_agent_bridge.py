#!/usr/bin/env python3
"""
Obsidian-Agent Bridge — Vault ↔ 에이전트 연결 상태 점검 및 양방향 I/O 헬퍼

사용법:
    python scripts/obsidian_agent_bridge.py         # 상태 점검 (기본)
    python scripts/obsidian_agent_bridge.py --check # 종료 코드 0=OK / 1=BROKEN
    python scripts/obsidian_agent_bridge.py --write-test  # 실제 쓰기 테스트
    python scripts/obsidian_agent_bridge.py --status      # 한 줄 상태 출력
"""

from __future__ import annotations

import argparse
import os
import socket
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "ObsidianVault"
AGENTBUS = VAULT / "10_AgentBus"

REQUIRED_DIRS = [
    AGENTBUS / "inbox",
    AGENTBUS / "outbox",
    AGENTBUS / "completed",
    AGENTBUS / "failed",
    AGENTBUS / "signals",
    AGENTBUS / "tasks",
]

OBSIDIAN_API_PORT = int(os.getenv("OBSIDIAN_API_PORT", "27123"))


def _iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def check_dirs() -> tuple[bool, list[str]]:
    missing = [str(d) for d in REQUIRED_DIRS if not d.exists()]
    return len(missing) == 0, missing


def check_obsidian_api() -> tuple[bool, str]:
    try:
        with socket.create_connection(("127.0.0.1", OBSIDIAN_API_PORT), timeout=1):
            return True, f"포트 {OBSIDIAN_API_PORT} 응답"
    except OSError:
        return False, f"포트 {OBSIDIAN_API_PORT} 응답 없음 (Obsidian 미실행 또는 REST API 플러그인 비활성)"


def check_write(dry_run: bool = True) -> tuple[bool, str]:
    signals_dir = AGENTBUS / "signals"
    signals_dir.mkdir(parents=True, exist_ok=True)
    test_file = signals_dir / "bridge_test.md"
    if dry_run:
        try:
            test_file.parent.stat()
            return True, "signals/ 디렉토리 접근 가능 (dry-run)"
        except OSError as e:
            return False, str(e)
    try:
        test_file.write_text(
            f"---\ntype: bridge-test\nstatus: ok\ncreated: {_iso()}\n---\n\nBridge write test OK.\n",
            encoding="utf-8",
        )
        return True, str(test_file.relative_to(ROOT))
    except OSError as e:
        return False, str(e)


def run_check(write_test: bool = False) -> dict:
    dirs_ok, missing = check_dirs()
    api_ok, api_msg = check_obsidian_api()
    write_ok, write_msg = check_write(dry_run=not write_test)

    overall = "OK" if (dirs_ok and write_ok) else "DEGRADED" if (dirs_ok or write_ok) else "BROKEN"
    if not dirs_ok and not write_ok:
        overall = "BROKEN"
    elif api_ok and dirs_ok and write_ok:
        overall = "OK"
    elif dirs_ok and write_ok:
        overall = "OK"

    return {
        "overall": overall,
        "dirs": {"ok": dirs_ok, "missing": missing},
        "obsidian_api": {"ok": api_ok, "msg": api_msg},
        "write": {"ok": write_ok, "msg": write_msg},
    }


def print_report(result: dict) -> None:
    status_icon = {"OK": "✅", "DEGRADED": "⚠️ ", "BROKEN": "❌"}.get(result["overall"], "?")
    print(f"\n{status_icon} Obsidian-Agent Bridge: {result['overall']}")
    print(f"   디렉토리  : {'✅ 정상' if result['dirs']['ok'] else '❌ 누락 ' + str(result['dirs']['missing'])}")
    print(f"   Obsidian  : {'✅' if result['obsidian_api']['ok'] else '⚠️ '} {result['obsidian_api']['msg']}")
    print(f"   쓰기 접근 : {'✅' if result['write']['ok'] else '❌'} {result['write']['msg']}")
    print()


def main() -> int:
    ap = argparse.ArgumentParser(description="Obsidian-Agent Bridge 상태 점검")
    ap.add_argument("--check", action="store_true", help="조용히 점검 후 종료 코드만 반환")
    ap.add_argument("--write-test", action="store_true", help="실제 파일 쓰기 테스트 수행")
    ap.add_argument("--status", action="store_true", help="한 줄 상태만 출력")
    args = ap.parse_args()

    # 누락된 디렉토리 자동 생성
    for d in REQUIRED_DIRS:
        d.mkdir(parents=True, exist_ok=True)

    result = run_check(write_test=args.write_test)

    if args.status:
        icon = {"OK": "✅", "DEGRADED": "⚠️", "BROKEN": "❌"}.get(result["overall"], "?")
        print(f"bridge:{result['overall']} {icon}")
        return 0 if result["overall"] in ("OK", "DEGRADED") else 1

    if args.check:
        return 0 if result["overall"] in ("OK", "DEGRADED") else 1

    print_report(result)
    return 0 if result["overall"] in ("OK", "DEGRADED") else 1


if __name__ == "__main__":
    sys.exit(main())
