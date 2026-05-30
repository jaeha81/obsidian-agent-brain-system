#!/usr/bin/env python3
"""
smoke_test.py — Card 2: 게이트 규칙 + CI 스모크 테스트

사용법:
    python scripts/smoke_test.py          # 전체 스모크 테스트
    python scripts/smoke_test.py --fast   # 핵심 5개 체크만
    python scripts/smoke_test.py --ci     # CI 모드 (실패 시 exit 1)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "ObsidianVault"
SCRIPTS = ROOT / "scripts"


@dataclass
class Result:
    name: str
    passed: bool
    detail: str
    elapsed: float = 0.0


def _run(name: str, fn) -> Result:
    t0 = time.monotonic()
    try:
        ok, detail = fn()
        return Result(name, ok, detail, time.monotonic() - t0)
    except Exception as exc:
        return Result(name, False, str(exc), time.monotonic() - t0)


# ── 체크 함수들 ──────────────────────────────────────────────────────────────

def check_required_files() -> tuple[bool, str]:
    required = [
        ROOT / "AGENTS.md",
        ROOT / "CLAUDE.md",
        VAULT / "00_System" / "ROUTING_RULES.md",
        VAULT / "00_System" / "BUCKY_OS_RUNBOOK.md",
        VAULT / "03_Projects" / "agents" / "bucky.md",
    ]
    missing = [str(f.relative_to(ROOT)) for f in required if not f.exists()]
    if missing:
        return False, "missing: " + ", ".join(missing)
    return True, f"all {len(required)} required files present"


def check_bucky_os_gate() -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "bucky_os_gate.py"), "--fast"],
        capture_output=True, text=True, cwd=ROOT
    )
    if result.returncode != 0:
        first_err = (result.stdout + result.stderr).strip().splitlines()
        return False, (first_err[0] if first_err else "gate failed")
    out = result.stdout.strip().splitlines()
    summary = next((l for l in out if "ok" in l.lower()), out[-1] if out else "ok")
    return True, summary


def check_context_pack_selector() -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "context_pack_selector.py"), "구현 작업"],
        capture_output=True, text=True, cwd=ROOT
    )
    if result.returncode != 0:
        return False, "selector failed: " + result.stderr.strip()[:80]
    return True, "selector returns packs for '구현 작업'"


def check_yaml_validator() -> tuple[bool, str]:
    # 00_System 폴더 내 최근 md 파일 한 개만 검증 (빠른 스모크용)
    sample_dir = VAULT / "00_System"
    mds = sorted(sample_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not mds:
        return True, "no md files to validate (skip)"
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "yaml_validator.py"), "--summary", str(mds[0])],
        capture_output=True, text=True, cwd=ROOT
    )
    out = (result.stdout + result.stderr).strip()
    lines = [l for l in out.splitlines() if l.strip() and "─" not in l]
    summary = lines[-1].strip() if lines else "ok"
    if result.returncode != 0:
        return False, summary[:80]
    return True, summary[:80]


def check_approve_task() -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "approve_task.py"), "list"],
        capture_output=True, text=True, cwd=ROOT
    )
    if result.returncode != 0:
        return False, "approve_task list failed: " + result.stderr.strip()[:60]
    return True, "approve_task list OK"


def check_obsidian_bridge() -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "obsidian_agent_bridge.py"), "--status"],
        capture_output=True, text=True, cwd=ROOT
    )
    if result.returncode != 0:
        return False, "bridge status failed: " + result.stderr.strip()[:60]
    return True, "obsidian_agent_bridge OK"


def check_agent_dispatcher_importable() -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, "-c", "import sys; sys.path.insert(0, 'scripts'); import agent_dispatcher; print('ok')"],
        capture_output=True, text=True, cwd=ROOT
    )
    if result.returncode != 0:
        return False, result.stderr.strip()[:80]
    return True, "agent_dispatcher importable"


def check_data_db_exists() -> tuple[bool, str]:
    db = ROOT / "data" / "channel_tasks.db"
    if not db.exists():
        return False, "channel_tasks.db not found"
    size = db.stat().st_size
    return True, f"channel_tasks.db exists ({size:,} bytes)"


FAST_CHECKS = [
    ("required_files", check_required_files),
    ("bucky_os_gate", check_bucky_os_gate),
    ("context_pack_selector", check_context_pack_selector),
    ("yaml_validator", check_yaml_validator),
    ("approve_task", check_approve_task),
]

FULL_CHECKS = FAST_CHECKS + [
    ("obsidian_bridge", check_obsidian_bridge),
    ("agent_dispatcher", check_agent_dispatcher_importable),
    ("channel_tasks_db", check_data_db_exists),
]


# ── 출력 ─────────────────────────────────────────────────────────────────────

def _icon(passed: bool) -> str:
    return "✅" if passed else "❌"


def print_results(results: list[Result], ci: bool = False) -> int:
    print("\n── JH-MultiAgent Smoke Test ─────────────────────────")
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    for r in results:
        bar = f"  {_icon(r.passed)}  {r.name:<30} {r.detail}  ({r.elapsed:.2f}s)"
        print(bar)
    print(f"\n{'─'*53}")
    print(f"  결과: {passed}/{total} 통과  {'✅ ALL PASS' if passed == total else '❌ FAIL'}")
    print()
    return 0 if passed == total else 1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true", help="핵심 5개 체크만")
    ap.add_argument("--ci", action="store_true", help="CI 모드 (실패 시 exit 1)")
    args = ap.parse_args()

    checks = FAST_CHECKS if args.fast else FULL_CHECKS
    results = [_run(name, fn) for name, fn in checks]
    code = print_results(results, ci=args.ci)

    if args.ci:
        sys.exit(code)


if __name__ == "__main__":
    main()
