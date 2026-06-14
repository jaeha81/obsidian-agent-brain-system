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
import tempfile
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

try:
    from cli_call_logger import log as _cli_log
    _CLI_LOG_ENABLED = True
except ImportError:
    def _cli_log(**kwargs) -> None:  # type: ignore[misc]
        pass
    _CLI_LOG_ENABLED = False


# Sonnet/Haiku/Opus 한도 초과 패턴 (Claude CLI stderr/stdout)
LIMIT_PATTERNS = re.compile(
    r"(usage limit|rate limit|hit your .* limit|사용 한도|한도에 도달|quota exceeded)",
    re.IGNORECASE,
)


LIMIT_PATTERNS = re.compile(
    r"(usage limit|rate limit|hit your .* limit|quota exceeded|subscription limit|"
    r"claude ai usage limit|exceeded .*usage|out of .*usage|resets .*(am|pm)|"
    r"too many requests|429|"
    r"사용\s*한도|구독\s*한도|한도\s*초과|할당량\s*초과)",
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


# Claude Code CLI 실행 파일 후보.
# npm 설치는 'claude.cmd'(Windows shim)를, 네이티브 인스톨러는 'claude'/'claude.exe'를 만든다.
# 설치 방식이 바뀌면 한쪽 이름이 사라지므로 PATH에서 대체 이름까지 탐색한다.
_CLAUDE_COMMAND_FALLBACKS = ("claude", "claude.exe", "claude.cmd", "claude.ps1")


def bucky_command() -> str:
    command = os.getenv("CLAUDE_COMMAND", "claude").strip() or "claude"
    if any(sep in command for sep in ("\\", "/", ":")):
        return command
    found = shutil.which(command)
    if found:
        return found
    # 설정된 이름을 PATH에서 못 찾으면 대체 실행 파일명으로 재탐색
    # (npm↔네이티브 설치 전환으로 claude.cmd → claude.exe 가 되는 회귀 대응)
    for alt in _CLAUDE_COMMAND_FALLBACKS:
        if alt == command:
            continue
        found = shutil.which(alt)
        if found:
            return found
    return command


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
    if tool_mode != "safe":
        cmd += ["--dangerously-skip-permissions"]
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
            return _invoke_bucky(
                prompt, system_prompt, timeout, attempt_model,
                with_tools=False, task_type=task_type or "", source="run_bucky",
            )
        except BuckyLimitError as exc:
            last_err = exc
            print(
                f"[bucky] ⚠️ {attempt_model} 한도 초과 → 다음 폴백 시도",
                file=sys.stderr,
            )
            continue
    if isinstance(last_err, BuckyLimitError):
        return _run_codex_after_claude_limit(
            prompt,
            system_prompt=system_prompt,
            timeout=timeout,
            with_tools=False,
            task_type=task_type or "",
            source="run_bucky_codex_on_limit",
        )
    raise last_err or BuckyError("All fallback models exhausted")


def _invoke_bucky(
    prompt: str,
    system_prompt: str | None,
    timeout: int | None,
    model: str,
    *,
    with_tools: bool,
    task_type: str = "",
    source: str = "",
) -> str:
    import time as _time
    # chat: 120s, code/tools: 300s, explicit override takes precedence
    if timeout:
        timeout_s = timeout
    elif task_type in ("code", "review", "debug"):
        timeout_s = int(os.getenv("BUCKY_TIMEOUT_CODE", "300"))
    elif with_tools:
        timeout_s = int(os.getenv("BUCKY_TIMEOUT_TOOLS", "300"))
    else:
        timeout_s = int(os.getenv("BUCKY_TIMEOUT", "120"))
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

    t0 = _time.monotonic()
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
    duration_ms = int((_time.monotonic() - t0) * 1000)

    success = result.returncode == 0
    output = _strip_preamble(result.stdout).strip() if success else ""

    _cli_log(
        command=bucky_command(),
        prompt=prompt,
        response=output or (result.stderr or result.stdout or "").strip(),
        success=success,
        duration_ms=duration_ms,
        model=model,
        task_type=task_type,
        source=source or ("with_tools" if with_tools else "no_tools"),
    )

    if not success:
        detail = (result.stderr or result.stdout or "").strip()
        if LIMIT_PATTERNS.search(detail):
            raise BuckyLimitError(f"{model} usage limit hit: {detail[:200]}")
        raise BuckyError(f"Bucky runtime failed with code {result.returncode}: {detail}")
    return output


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
    if isinstance(last_err, BuckyLimitError):
        return _run_codex_after_claude_limit(
            prompt,
            system_prompt=system_prompt,
            timeout=timeout,
            with_tools=True,
            task_type=task_type or "",
            source="run_bucky_with_tools_codex_on_limit",
        )
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


def _codex_on_limit_enabled() -> bool:
    return os.getenv("BUCKY_CODEX_ON_LIMIT", "1").strip() != "0"


def _run_codex_after_claude_limit(
    prompt: str,
    *,
    system_prompt: str | None,
    timeout: int | None,
    with_tools: bool,
    task_type: str,
    source: str,
) -> str:
    if not _codex_on_limit_enabled():
        raise BuckyLimitError("Claude usage limit hit and Codex fallback is disabled")
    if not is_codex_available():
        raise BuckyLimitError(
            f"Claude usage limit hit and Codex CLI not found. CODEX_COMMAND={codex_command()!r}"
        )
    print("[bucky] Claude limit hit -> running Codex-only fallback", file=sys.stderr)
    return _invoke_codex(
        prompt,
        system_prompt=system_prompt,
        timeout=timeout,
        with_tools=with_tools,
        task_type=task_type,
        source=source,
    )


def _invoke_codex(
    prompt: str,
    *,
    system_prompt: str | None,
    timeout: int | None,
    with_tools: bool,
    task_type: str,
    source: str,
) -> str:
    import time as _time

    timeout_s = timeout or int(os.getenv("CODEX_TIMEOUT", os.getenv("BUCKY_TIMEOUT_CODE", "300")))
    if with_tools:
        sandbox = os.getenv("CODEX_TOOLS_SANDBOX", "workspace-write").strip() or "workspace-write"
    else:
        sandbox = os.getenv("CODEX_SANDBOX", "read-only").strip() or "read-only"
    model = os.getenv("CODEX_MODEL", "").strip()

    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w", encoding="utf-8") as tf:
        output_path = tf.name

    try:
        cmd = [
            codex_command(),
            "exec",
            "-C",
            str(ROOT),
            "--sandbox",
            sandbox,
            "--output-last-message",
            output_path,
            "-",
        ]
        if model:
            cmd[2:2] = ["--model", model]

        effective_prompt = prompt
        if system_prompt:
            effective_prompt = f"{system_prompt.strip()}\n\n{prompt}"

        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        t0 = _time.monotonic()
        result = subprocess.run(
            cmd,
            input=effective_prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
            timeout=timeout_s,
            env=env,
        )
        duration_ms = int((_time.monotonic() - t0) * 1000)

        out_path = Path(output_path)
        output = out_path.read_text(encoding="utf-8").strip() if out_path.exists() else result.stdout.strip()
        success = result.returncode == 0
        detail = output or (result.stderr or result.stdout or "").strip()

        _cli_log(
            command=codex_command(),
            prompt=effective_prompt,
            response=detail,
            success=success,
            duration_ms=duration_ms,
            model=model or "codex-default",
            task_type=task_type,
            source=source,
        )

        if not success:
            raise BuckyError(f"Codex fallback failed with code {result.returncode}: {detail[:400]}")
        return output
    finally:
        try:
            Path(output_path).unlink(missing_ok=True)
        except Exception:
            pass


def _strip_preamble(text: str) -> str:
    """Remove CLAUDE.md PC-detection preamble lines from the start of the response."""
    return re.sub(r'^[🏠💻🏢][^\n]*\n+(?:-{3,}\n+)?', '', text, count=1)
