#!/usr/bin/env python3
"""Bucky Agent CLI wrapper.

Bucky는 메인 오케스트레이터 에이전트다.
내부적으로 Claude Code CLI (claude_cli 런타임)를 통해 AI 추론을 실행한다.

Supported runtimes:
- claude_cli: Claude Code CLI subscription/login flow (기본, 권장)
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


class BuckyError(RuntimeError):
    """Raised when the Bucky CLI runtime is missing or returns a non-zero exit."""


def _split_env_args(value: str) -> list[str]:
    if not value.strip():
        return []
    return shlex.split(value, posix=False)


def bucky_command() -> str:
    command = os.getenv("CLAUDE_COMMAND", "claude").strip() or "claude"
    if any(sep in command for sep in ("\\", "/", ":")):
        return command
    return shutil.which(command) or command


def agent_runtime() -> str:
    return os.getenv("AGENT_RUNTIME", "claude_cli").strip().lower() or "claude_cli"


def is_bucky_available() -> bool:
    command = bucky_command()
    if any(sep in command for sep in ("\\", "/", ":")):
        return Path(command).exists()
    return shutil.which(command) is not None


def build_bucky_command() -> list[str]:
    command = bucky_command()
    return [
        command,
        "--output-format",
        os.getenv("CLAUDE_OUTPUT_FORMAT", "text").strip() or "text",
    ]


def run_bucky(prompt: str, *, timeout: int | None = None) -> str:
    if not is_bucky_available():
        raise BuckyError(
            f"Bucky CLI not found. CLAUDE_COMMAND={bucky_command()!r} — "
            "Claude Code CLI가 설치되어 있는지 확인하세요."
        )

    timeout_s = timeout or int(os.getenv("BUCKY_TIMEOUT", "900"))
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["BUCKY_SUBPROCESS"] = "1"  # prevents awareness hook from logging Bucky's own sessions
    # 구독 전용: API 키 무조건 제거 (과금 경로 차단)
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("CLAUDE_API_KEY", None)

    result = subprocess.run(
        build_bucky_command(),
        input=prompt,
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
        raise BuckyError(f"Bucky runtime failed with code {result.returncode}: {detail}")
    return result.stdout.strip()
