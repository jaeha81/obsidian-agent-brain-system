#!/usr/bin/env python3
"""Read-only startup checks for the 3-PC Bucky/Codex/Claude workflow."""

from __future__ import annotations

import argparse
import io
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_VAULT = ROOT / "ObsidianVault"

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf-8-sig"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf-8-sig"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def _load_env() -> None:
    if load_dotenv:
        load_dotenv(ROOT / ".env", encoding="utf-8", override=True)


def _run(args: list[str], timeout: int = 10) -> tuple[int, str]:
    try:
        result = subprocess.run(
            args,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return result.returncode, (result.stdout + result.stderr).strip()
    except Exception as exc:
        return 1, str(exc)


def _check_git() -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    code, branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    rows.append(("git_branch", branch if code == 0 else f"FAIL {branch}"))

    code, status = _run(["git", "status", "--short"])
    rows.append(("git_worktree", "clean" if code == 0 and not status else f"WARN {status or 'git status failed'}"))

    code, upstream = _run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    if code != 0:
        rows.append(("git_upstream", "WARN no upstream"))
        return rows

    fetch_code, fetch_output = _run(["git", "fetch", "--dry-run"], timeout=20)
    if fetch_code != 0:
        rows.append(("git_fetch", f"WARN fetch check failed: {fetch_output}"))
    code, counts = _run(["git", "rev-list", "--left-right", "--count", f"HEAD...{upstream}"])
    if code == 0:
        ahead, behind = counts.split()[:2]
        state = "ok" if ahead == "0" and behind == "0" else f"WARN ahead={ahead} behind={behind}"
        rows.append(("git_sync", state))
    else:
        rows.append(("git_sync", f"WARN {counts}"))
    return rows


def _check_paths() -> list[tuple[str, str]]:
    vault = Path(os.getenv("VAULT_PATH", str(DEFAULT_VAULT)))
    shared_env = os.getenv("JH_SHARED_PATH", "").strip()
    room_env = os.getenv("JH_AGENT_ROOM_PATH", "").strip()
    legacy_enabled = os.getenv("BUCKY_ENABLE_LEGACY_CONTEXT", "0").strip().lower() in {"1", "true", "yes", "on"}
    shared = Path(shared_env) if shared_env else None
    room = Path(room_env) if room_env else None
    shared_state = "not configured (ok)" if shared is None else ("enabled reference-only" if legacy_enabled and shared.exists() else "configured but inactive (ok)")
    room_state = "not configured (ok)" if room is None else ("enabled reference-only" if legacy_enabled and room.exists() else "configured but inactive (ok)")
    return [
        ("repo", str(ROOT)),
        ("vault_path", "ok" if vault.exists() else f"FAIL missing {vault}"),
        ("legacy_jh_shared", shared_state),
        ("legacy_jh_agent_room", room_state),
        ("env_file", "ok" if (ROOT / ".env").exists() else "WARN missing .env"),
    ]


def _check_claude_sync() -> list[tuple[str, str]]:
    """Verify the two-layer CLAUDE.md structure: global (all-projects) and
    project (this repo) are deliberately separate files that cross-reference
    each other, not a single file synced/overwritten in both places."""
    source = ROOT / "CLAUDE.md"
    dest = Path.home() / ".claude" / "CLAUDE.md"
    if not source.exists():
        return [("claude_source", f"WARN missing {source}")]
    if not dest.exists():
        return [("claude_md", f"WARN missing {dest}")]
    source_text = source.read_text(encoding="utf-8", errors="replace")
    dest_text = dest.read_text(encoding="utf-8", errors="replace")
    source_points_to_dest = ".claude\\CLAUDE.md" in source_text or ".claude/CLAUDE.md" in source_text
    dest_points_to_source = "obsidian-agent-brain-system" in dest_text.lower()
    if source_points_to_dest and dest_points_to_source:
        return [("claude_md", "ok two-layer structure linked (global + project cross-reference)")]
    return [("claude_md", "WARN two-layer cross-reference missing (project/global CLAUDE.md should point at each other)")]


def _check_bucky_os_gate() -> list[tuple[str, str]]:
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import bucky_os_gate  # type: ignore

        checks = bucky_os_gate.run_checks()
    except Exception as exc:
        return [("bucky_os_gate", f"WARN unavailable: {exc}")]

    failed = [check for check in checks if not check.passed]
    if failed:
        detail = "; ".join(f"{check.name}: {check.detail}" for check in failed[:3])
        return [("bucky_os_gate", f"FAIL {detail}")]
    return [("bucky_os_gate", f"ok {len(checks)} checks")]


def _check_commands(docker_mode: bool) -> list[tuple[str, str]]:
    rows = []
    for env_name, default in (("CLAUDE_COMMAND", "claude"), ("CODEX_COMMAND", "codex")):
        command = os.getenv(env_name, default).strip() or default
        exists = Path(command).exists() if any(sep in command for sep in ("\\", "/", ":")) else shutil.which(command)
        label = env_name.lower()
        if exists:
            rows.append((label, "ok"))
        elif docker_mode:
            rows.append((label, "WARN missing in container; use host-cli profile only after CLI/auth mounted"))
        else:
            rows.append((label, f"WARN missing {command}"))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Check 3-PC Bucky/Codex/Claude readiness.")
    parser.add_argument("--docker", action="store_true", help="Report container-specific CLI caveats.")
    args = parser.parse_args()

    _load_env()
    rows = []
    rows.extend(_check_paths())
    rows.extend(_check_git())
    rows.extend(_check_claude_sync())
    rows.extend(_check_bucky_os_gate())
    rows.extend(_check_commands(args.docker))

    print("[preflight]")
    failed = False
    warned = False
    for key, value in rows:
        print(f"{key}: {value}")
        failed = failed or value.startswith("FAIL")
        warned = warned or value.startswith("WARN") or "WARN " in value

    if failed:
        return 2
    if warned:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
