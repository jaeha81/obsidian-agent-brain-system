#!/usr/bin/env python3
"""Read-only startup checks for the 3-PC Bucky/Codex/Claude workflow."""

from __future__ import annotations

import argparse
import hashlib
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


def _md5(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.md5(path.read_bytes()).hexdigest()


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
    shared = Path(os.getenv("JH_SHARED_PATH", "G:/내 드라이브/JH-SHARED"))
    room = Path(os.getenv("JH_AGENT_ROOM_PATH", "G:/내 드라이브/JH-Agent-Room"))
    return [
        ("repo", str(ROOT)),
        ("vault_path", "ok" if vault.exists() else f"FAIL missing {vault}"),
        ("jh_shared", "ok" if shared.exists() else f"WARN missing {shared}"),
        ("jh_agent_room", "ok" if room.exists() else f"WARN missing {room}"),
        ("env_file", "ok" if (ROOT / ".env").exists() else "WARN missing .env"),
    ]


def _check_claude_sync() -> list[tuple[str, str]]:
    source = DEFAULT_VAULT / "05_Frameworks" / "guides" / "CLAUDE_MASTER.md"
    dest = Path.home() / ".claude" / "CLAUDE.md"
    source_hash = _md5(source)
    dest_hash = _md5(dest)
    if not source_hash:
        return [("claude_master", f"WARN missing {source}")]
    if not dest_hash:
        return [("claude_md", f"WARN missing {dest}")]
    if source_hash == dest_hash:
        return [("claude_md", "ok exact match")]
    code, output = _run([sys.executable, "scripts/sync_claude_instructions.py", "--check"])
    state = "ok" if code == 0 else "WARN sync needed"
    return [("claude_md", f"{state}: {output}")]


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
