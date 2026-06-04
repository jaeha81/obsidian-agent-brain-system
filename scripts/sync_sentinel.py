#!/usr/bin/env python3
"""Read-only multi-PC sync sentinel for the Obsidian Agent Brain System."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
from pathlib import Path
from typing import Callable

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional runtime dependency
    load_dotenv = None


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_VAULT = ROOT / "ObsidianVault"
CommandRunner = Callable[[list[str]], tuple[int, str]]
KNOWN_PC_ROLES = {"primary", "secondary"}
KNOWN_PC_NAMES = {"home", "office", "laptop"}


def load_local_env() -> None:
    if load_dotenv:
        load_dotenv(ROOT / ".env", encoding="utf-8", override=True)


def normalize_pc_role(value: str | None) -> str:
    role = (value or "").strip().lower()
    return role if role in KNOWN_PC_ROLES else "secondary"


def normalize_pc_name(value: str | None) -> str:
    name = (value or "").strip().lower()
    return name if name in KNOWN_PC_NAMES else "unknown"


def path_exists(path: Path) -> bool:
    try:
        return path.exists()
    except OSError:
        return False


def classify_storage(path: Path) -> str:
    text = str(path).replace("\\", "/").lower()
    if "내 드라이브" in text or "google drive" in text or text.startswith("g:/"):
        return "google_drive"
    return "local_only"


def run_command(args: list[str]) -> tuple[int, str]:
    try:
        result = subprocess.run(
            args,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        return result.returncode, (result.stdout + result.stderr).strip()
    except Exception as exc:
        return 1, str(exc)


def git_status(command_runner: CommandRunner = run_command) -> dict[str, str]:
    branch_code, branch = command_runner(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    status_code, status = command_runner(["git", "status", "--short"])
    return {
        "branch": branch if branch_code == 0 and branch else "unknown",
        "worktree": "clean" if status_code == 0 and not status else "dirty_or_unknown",
        "status": status if status_code == 0 else f"git status failed: {status}",
    }


def docker_status(command_runner: CommandRunner = run_command) -> str:
    code, _output = command_runner(["docker", "--version"])
    return "available" if code == 0 else "missing"


def build_report(
    *,
    root: Path = ROOT,
    vault: Path = DEFAULT_VAULT,
    env: dict[str, str] | None = None,
    hostname: str | None = None,
    command_runner: CommandRunner = run_command,
) -> dict:
    source_env = env if env is not None else os.environ
    raw_pc_role = source_env.get("PC_ROLE")
    raw_pc_name = source_env.get("PC_NAME")
    pc_role = normalize_pc_role(raw_pc_role)
    pc_name = normalize_pc_name(raw_pc_name)
    host = hostname or socket.gethostname()
    storage = classify_storage(root)
    vault_storage = classify_storage(vault)
    warnings: list[str] = []

    if not raw_pc_role or not raw_pc_name:
        warnings.append("pc_identity_unconfigured")
    elif pc_role != raw_pc_role.strip().lower() or pc_name != raw_pc_name.strip().lower():
        warnings.append("pc_identity_invalid")
    if pc_role == "primary" and pc_name != "home":
        warnings.append("primary_pc_name_not_home")
    if pc_role != "primary":
        warnings.append("secondary_pc_canonical_write_risk")
    if storage != "google_drive" and vault_storage != "google_drive":
        warnings.append("local_only_storage")
    if not path_exists(vault):
        warnings.append("vault_path_missing")

    git = git_status(command_runner)
    if git["worktree"] != "clean":
        warnings.append("git_worktree_not_clean")

    docker = docker_status(command_runner)
    runtime_risk = "warning" if warnings else "none"

    return {
        "pc": {"role": pc_role, "name": pc_name, "hostname": host},
        "workspace": str(root),
        "vault": str(vault),
        "storage": storage,
        "vault_storage": vault_storage,
        "git": git,
        "docker": docker,
        "runtime_risk": runtime_risk,
        "warnings": warnings,
        "next_action": "review warnings before canonical writes" if warnings else "safe to continue",
    }


def format_text(report: dict) -> str:
    warnings = ", ".join(report["warnings"]) if report["warnings"] else "none"
    return "\n".join(
        [
            "[Sync Sentinel]",
            f"PC: {report['pc']['name']} ({report['pc']['role']})",
            f"Host: {report['pc']['hostname']}",
            f"Workspace: {report['workspace']}",
            f"Vault: {report['vault']}",
            f"Storage: {report['storage']}",
            f"Git: {report['git']['branch']} / {report['git']['worktree']}",
            f"Docker: {report['docker']}",
            f"Runtime risk: {report['runtime_risk']}",
            f"Warnings: {warnings}",
            f"Next action: {report['next_action']}",
        ]
    )


def main() -> int:
    load_local_env()

    parser = argparse.ArgumentParser(description="Check multi-PC sync and storage safety.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--vault", type=Path, default=Path(os.getenv("VAULT_PATH", str(DEFAULT_VAULT))))
    args = parser.parse_args()

    report = build_report(vault=args.vault)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_text(report))
    return 1 if report["runtime_risk"] == "warning" else 0


if __name__ == "__main__":
    raise SystemExit(main())
