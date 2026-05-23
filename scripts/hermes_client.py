#!/usr/bin/env python3
"""Small wrapper for calling the configured local agent from scripts.

Supported runtimes:
- hermes: Hermes Agent CLI
- claude_cli: Claude Code CLI subscription/login flow
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env", encoding="utf-8", override=True)


class HermesError(RuntimeError):
    """Raised when the configured agent CLI is missing or returns a non-zero exit."""


def _split_env_args(value: str) -> list[str]:
    if not value.strip():
        return []
    return shlex.split(value, posix=False)


def hermes_command() -> str:
    if agent_runtime() == "claude_cli":
        command = os.getenv("CLAUDE_COMMAND", "claude").strip() or "claude"
    else:
        command = os.getenv("HERMES_COMMAND", "hermes").strip() or "hermes"

    if any(sep in command for sep in ("\\", "/", ":")):
        return command
    return shutil.which(command) or command


def agent_runtime() -> str:
    return os.getenv("AGENT_RUNTIME", "hermes").strip().lower() or "hermes"


def is_hermes_available() -> bool:
    command = hermes_command()
    if any(sep in command for sep in ("\\", "/", ":")):
        return Path(command).exists()
    return shutil.which(command) is not None


def build_hermes_command(prompt: str) -> list[str]:
    command = hermes_command()
    if agent_runtime() == "claude_cli":
        return [
            command,
            "-p",
            prompt,
            "--output-format",
            os.getenv("CLAUDE_OUTPUT_FORMAT", "text").strip() or "text",
        ]

    mode = os.getenv("HERMES_MODE", "oneshot").strip().lower()
    args: list[str] = [command]

    profile = os.getenv("HERMES_PROFILE", "").strip()
    if profile:
        args.extend(["-p", profile])

    if mode == "chat":
        args.extend(["chat", "--quiet", "-q", prompt])
    else:
        args.extend(["-z", prompt])

    provider = os.getenv("HERMES_PROVIDER", "").strip()
    if provider:
        args.extend(["--provider", provider])

    model = os.getenv("HERMES_MODEL", "").strip()
    if model:
        args.extend(["--model", model])

    toolsets = os.getenv("HERMES_TOOLSETS", "").strip()
    if toolsets:
        args.extend(["--toolsets", toolsets])

    skills = os.getenv("HERMES_SKILLS", "").strip()
    if skills:
        args.extend(["--skills", skills])

    args.extend(_split_env_args(os.getenv("HERMES_EXTRA_ARGS", "")))
    return args


def run_hermes(prompt: str, *, timeout: int | None = None) -> str:
    if not is_hermes_available():
        raise HermesError(
            f"Agent CLI not found. Set AGENT_RUNTIME/HERMES_COMMAND/CLAUDE_COMMAND. "
            f"Tried: {hermes_command()}"
        )

    timeout_s = timeout or int(os.getenv("HERMES_TIMEOUT", "900"))
    env = os.environ.copy()
    if agent_runtime() == "claude_cli" and os.getenv("CLAUDE_USE_API_KEY", "0") != "1":
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("CLAUDE_API_KEY", None)

    result = subprocess.run(
        build_hermes_command(prompt),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
        timeout=timeout_s,
        env=env,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise HermesError(f"Agent runtime failed with code {result.returncode}: {detail}")
    return result.stdout.strip()
