#!/usr/bin/env python3
"""
CLI 호출 결과 JSONL + Markdown 동시 기록 — 3단계 구현.

기록 대상: bucky_client.run_bucky() 호출 (Claude CLI 구독 경로)
출력:
  ObsidianVault/05_Logs/cli-tools.jsonl   — 구조화 로그 (append)
  ObsidianVault/05_Logs/cli-tools-{date}.md — 날짜별 Markdown (append)

필드: command, prompt_summary, response_summary, success, duration_ms,
       model, task_type, timestamp
"""

import json
import os
import threading
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).parent.parent
_VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
_LOG_DIR = _VAULT / "05_Logs"

_JSONL_PATH = _LOG_DIR / "cli-tools.jsonl"

_lock = threading.Lock()

_PROMPT_PREVIEW = int(os.getenv("CLI_LOG_PROMPT_LEN", "200"))
_RESPONSE_PREVIEW = int(os.getenv("CLI_LOG_RESPONSE_LEN", "300"))


def _truncate(text: str, limit: int) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


def log(
    *,
    command: str,
    prompt: str,
    response: str,
    success: bool,
    duration_ms: int,
    model: str = "",
    task_type: str = "",
    source: str = "",
) -> None:
    """CLI 호출 결과 기록. 실패해도 예외를 발생시키지 않는다."""
    try:
        _write(
            command=command,
            prompt=prompt,
            response=response,
            success=success,
            duration_ms=duration_ms,
            model=model,
            task_type=task_type,
            source=source,
        )
    except Exception as exc:
        print(f"[CLILogger] 기록 실패 (무시): {exc}", flush=True)


def _write(
    *,
    command: str,
    prompt: str,
    response: str,
    success: bool,
    duration_ms: int,
    model: str,
    task_type: str,
    source: str,
) -> None:
    now = datetime.now()
    iso = now.isoformat(timespec="seconds")
    date_str = now.strftime("%Y-%m-%d")

    prompt_s = _truncate(prompt, _PROMPT_PREVIEW)
    response_s = _truncate(response, _RESPONSE_PREVIEW)

    entry = {
        "timestamp": iso,
        "command": command,
        "model": model,
        "task_type": task_type,
        "source": source,
        "success": success,
        "duration_ms": duration_ms,
        "prompt_summary": prompt_s,
        "response_summary": response_s,
    }

    md_path = _LOG_DIR / f"cli-tools-{date_str}.md"
    status_icon = "✅" if success else "❌"
    md_block = (
        f"\n## {iso} — {command} [{model}]\n\n"
        f"- 결과: {status_icon} | 소요: `{duration_ms}ms` | task_type: `{task_type or '-'}`\n"
        f"- source: `{source or '-'}`\n"
        f"- **프롬프트**: {prompt_s}\n"
        f"- **응답 요약**: {response_s}\n"
    )

    with _lock:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(str(_JSONL_PATH), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        with open(str(md_path), "a", encoding="utf-8") as f:
            if md_path.stat().st_size == 0:
                f.write(f"---\ntype: cli-call-log\ndate: {date_str}\n---\n\n# CLI 호출 로그 {date_str}\n")
            f.write(md_block)
