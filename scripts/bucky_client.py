#!/usr/bin/env python3
"""Bucky Agent CLI wrapper.

Bucky는 메인 오케스트레이터 에이전트다.
내부적으로 Claude Code CLI (claude_cli 런타임)를 통해 AI 추론을 실행한다.

Supported runtimes:
- claude_cli: Claude Code CLI subscription/login flow (기본, 권장)
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env", encoding="utf-8", override=True)

# 모델 라우터 통합 (작업 유형 → sonnet/haiku/opus)
SCRIPTS_DIR = Path(__file__).parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
try:
    from model_router import select_model, fallback_chain  # type: ignore
except Exception:  # router 없을 때도 동작
    def select_model(task_type: str, override: str | None = None) -> str:  # type: ignore
        return override or "sonnet"
    def fallback_chain(primary: str) -> list[str]:  # type: ignore
        return [primary]


# Sonnet/Haiku/Opus 한도 초과 패턴 (Claude CLI stderr/stdout)
LIMIT_PATTERNS = re.compile(
    r"(usage limit|rate limit|hit your .* limit|사용 한도|한도에 도달|quota exceeded)",
    re.IGNORECASE,
)


class BuckyError(RuntimeError):
    """Raised when the Bucky CLI runtime is missing or returns a non-zero exit."""


class BuckyLimitError(BuckyError):
    """Raised when the model hit its usage limit (so caller can fall back)."""


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


def resolve_model(task_type: str | None = None, override: str | None = None) -> str:
    """모델 결정 우선순위:
       1. override (명시적 model=)
       2. BUCKY_FORCE_MODEL env (강제 — 한도 초과 회피용)
       3. task_type 라우팅 (호출자가 의도 명시)
       4. BUCKY_CHAT_MODEL env (디폴트 모델)
       5. sonnet
    """
    if override:
        return override
    force = os.getenv("BUCKY_FORCE_MODEL", "").strip()
    if force:
        return force
    if task_type:
        return select_model(task_type)
    env_default = os.getenv("BUCKY_CHAT_MODEL", "").strip()
    if env_default:
        return env_default
    return "sonnet"


def build_bucky_command(system_prompt: str | None = None, model: str | None = None) -> list[str]:
    command = bucky_command()
    if model is None:
        model = os.getenv("BUCKY_CHAT_MODEL", "sonnet").strip() or "sonnet"
    tool_mode = os.getenv("BUCKY_TOOL_MODE", "safe").strip() or "safe"

    cmd = [
        command,
        "--print",
        "--output-format", os.getenv("CLAUDE_OUTPUT_FORMAT", "text").strip() or "text",
        "--model", model,
        "--no-session-persistence",
    ]
    if system_prompt:
        cmd += ["--append-system-prompt", system_prompt]
    if tool_mode == "safe":
        cmd += ["--tools", ""]                           # no tools → no permission prompts
    else:
        cmd += ["--dangerously-skip-permissions"]        # auto-approve all tool calls
    return cmd


def run_bucky(
    prompt: str,
    *,
    system_prompt: str | None = None,
    timeout: int | None = None,
    task_type: str | None = None,
    model: str | None = None,
    enable_fallback: bool | None = None,
) -> str:
    """Sonnet/Haiku/Opus 자동 라우팅 + 한도 초과 시 폴백.

    Args:
        task_type: 작업 유형 (model_router.TASK_TO_MODEL 키). 미지정 시 sonnet.
        model: 명시적 모델 override. task_type보다 우선.
        enable_fallback: 한도 초과 시 폴백 체인 시도. None이면 env BUCKY_FALLBACK=1로 결정.
    """
    if not is_bucky_available():
        raise BuckyError(
            f"Bucky CLI not found. CLAUDE_COMMAND={bucky_command()!r} — "
            "Claude Code CLI가 설치되어 있는지 확인하세요."
        )

    primary = resolve_model(task_type, model)
    if enable_fallback is None:
        enable_fallback = os.getenv("BUCKY_FALLBACK", "1").strip() != "0"
    chain = fallback_chain(primary) if enable_fallback else [primary]

    last_err: BuckyError | None = None
    for attempt_model in chain:
        try:
            return _invoke_bucky(prompt, system_prompt, timeout, attempt_model, with_tools=False)
        except BuckyLimitError as exc:
            last_err = exc
            print(
                f"[bucky] ⚠️ {attempt_model} 한도 초과 → 다음 폴백 시도",
                file=sys.stderr,
            )
            continue
    raise last_err or BuckyError("All fallback models exhausted")


def _invoke_bucky(
    prompt: str,
    system_prompt: str | None,
    timeout: int | None,
    model: str,
    *,
    with_tools: bool,
) -> str:
    timeout_s = timeout or int(os.getenv("BUCKY_TIMEOUT", "900"))
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["BUCKY_SUBPROCESS"] = "1"
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("CLAUDE_API_KEY", None)

    if with_tools:
        cmd = [
            bucky_command(),
            "--print",
            "--output-format", os.getenv("CLAUDE_OUTPUT_FORMAT", "text").strip() or "text",
            "--model", model,
            "--no-session-persistence",
            "--dangerously-skip-permissions",
        ]
        if system_prompt:
            cmd += ["--append-system-prompt", system_prompt]
    else:
        cmd = build_bucky_command(system_prompt, model=model)

    result = subprocess.run(
        cmd,
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
        if LIMIT_PATTERNS.search(detail):
            raise BuckyLimitError(f"{model} usage limit hit: {detail[:200]}")
        raise BuckyError(f"Bucky runtime failed with code {result.returncode}: {detail}")
    return _strip_preamble(result.stdout).strip()


def run_bucky_with_tools(
    prompt: str,
    *,
    system_prompt: str | None = None,
    timeout: int | None = None,
    task_type: str | None = None,
    model: str | None = None,
    enable_fallback: bool | None = None,
) -> str:
    """run_bucky와 동일하나 --dangerously-skip-permissions 강제 적용.

    작업 채널(jh-work-*) 전용. 파일 읽기/쓰기/실행 도구 모두 허용.
    task_type 기반 모델 라우팅 + 한도 초과 폴백 지원.
    """
    if not is_bucky_available():
        raise BuckyError(
            f"Bucky CLI not found. CLAUDE_COMMAND={bucky_command()!r} — "
            "Claude Code CLI가 설치되어 있는지 확인하세요."
        )

    primary = resolve_model(task_type, model)
    if enable_fallback is None:
        enable_fallback = os.getenv("BUCKY_FALLBACK", "1").strip() != "0"
    chain = fallback_chain(primary) if enable_fallback else [primary]

    last_err: BuckyError | None = None
    for attempt_model in chain:
        try:
            return _invoke_bucky(prompt, system_prompt, timeout, attempt_model, with_tools=True)
        except BuckyLimitError as exc:
            last_err = exc
            print(
                f"[bucky] ⚠️ {attempt_model} 한도 초과 → 다음 폴백 시도",
                file=sys.stderr,
            )
            continue
    raise last_err or BuckyError("All fallback models exhausted")


def codex_command() -> str:
    command = os.getenv("CODEX_COMMAND", "codex").strip() or "codex"
    if any(sep in command for sep in ("\\", "/", ":")):
        return command
    return shutil.which(command) or command


def is_codex_available() -> bool:
    command = codex_command()
    if any(sep in command for sep in ("\\", "/", ":")):
        return Path(command).exists()
    return shutil.which(command) is not None


def _strip_preamble(text: str) -> str:
    """Remove CLAUDE.md PC-detection preamble lines from the start of the response."""
    return re.sub(r'^[🏠💻🏢][^\n]*\n+(?:-{3,}\n+)?', '', text, count=1)
