"""Claude Code status line helper.

Reads Claude Code status JSON from stdin and prints one concise line with:
- current chat/session id
- approximate context usage from the latest transcript usage record
- model and current folder
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


DEFAULT_CONTEXT_LIMIT = 200_000


def _read_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _short_session(session_id: str) -> str:
    clean = (session_id or "unknown").strip()
    if len(clean) <= 8:
        return clean or "unknown"
    return clean[:8]


def _format_tokens(tokens: int) -> str:
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.1f}m"
    if tokens >= 1_000:
        return f"{tokens / 1_000:.1f}k"
    return str(max(tokens, 0))


def _latest_context_tokens(transcript_path: str | None) -> int:
    if not transcript_path:
        return 0

    path = Path(transcript_path)
    if not path.exists() or not path.is_file():
        return 0

    latest = 0
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if '"usage"' not in line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                usage = _extract_usage(event)
                if usage:
                    latest = _usage_context_tokens(usage)
    except OSError:
        return 0

    return latest


def _extract_usage(event: dict[str, Any]) -> dict[str, Any] | None:
    message = event.get("message")
    if isinstance(message, dict) and isinstance(message.get("usage"), dict):
        return message["usage"]
    if isinstance(event.get("usage"), dict):
        return event["usage"]
    return None


def _usage_context_tokens(usage: dict[str, Any]) -> int:
    total = 0
    for key in (
        "input_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
    ):
        value = usage.get(key, 0)
        if isinstance(value, int):
            total += value
    return total


def _context_limit(data: dict[str, Any]) -> int:
    env_value = os.environ.get("CLAUDE_CONTEXT_LIMIT", "")
    if env_value.isdigit():
        return int(env_value)

    model_id = str(data.get("model", {}).get("id", "")).lower()
    if "haiku" in model_id or "sonnet" in model_id or "opus" in model_id:
        return DEFAULT_CONTEXT_LIMIT
    return DEFAULT_CONTEXT_LIMIT


def main() -> int:
    data = _read_stdin_json()

    session = _short_session(str(data.get("session_id", "")))
    model = data.get("model", {}).get("display_name") or data.get("model", {}).get("id") or "model"
    workspace = data.get("workspace", {})
    current_dir = workspace.get("current_dir") or data.get("cwd") or ""
    folder = Path(str(current_dir)).name or "workspace"

    tokens = _latest_context_tokens(data.get("transcript_path"))
    limit = _context_limit(data)
    percent = round((tokens / limit) * 100) if limit and tokens else 0

    if percent >= 90:
        alert = " !! CRITICAL - /compact NOW"
    elif percent >= 75:
        alert = " ! WARNING - new session soon"
    elif percent >= 50:
        alert = " * 50%+ - monitor context"
    else:
        alert = ""

    print(
        "SESSION "
        f"{session} | CTX {_format_tokens(tokens)}/{_format_tokens(limit)} {percent}%{alert} "
        f"| {model} | {folder}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
