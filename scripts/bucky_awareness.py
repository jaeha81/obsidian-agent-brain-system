#!/usr/bin/env python3
"""Hook: notifies Bucky of external Claude Code / Codex instructions.

Triggered by:
- UserPromptSubmit: any Claude Code session receives a prompt
- PostToolUse(codex): Codex MCP tool is called

Writes to ObsidianVault/10_AgentBus/awareness/YYYY-MM-DD.jsonl
Also updates LATEST.md for quick Bucky inspection.

Skips silently when BUCKY_SUBPROCESS=1 (Bucky's own spawned sessions).
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
VAULT = ROOT / "ObsidianVault"
AWARENESS_DIR = VAULT / "10_AgentBus" / "awareness"
LATEST_FILE = AWARENESS_DIR / "LATEST.md"
MAX_LATEST = 10


def _update_latest(record: dict) -> None:
    entries: list[str] = []
    if LATEST_FILE.exists():
        lines = LATEST_FILE.read_text(encoding="utf-8").splitlines()
        # collect existing entry lines (skip header)
        entries = [l for l in lines if l.startswith("- ")]

    ts = record["ts"]
    source = record.get("source", record.get("event", "?"))
    cwd = record.get("cwd", "")
    preview = record.get("prompt_preview") or record.get("input_preview") or ""
    preview_short = preview.replace("\n", " ")[:120]

    entry = f"- `{ts}` [{source}] `{Path(cwd).name}` — {preview_short}"
    entries.insert(0, entry)
    entries = entries[:MAX_LATEST]

    content = "# Bucky Awareness — Last External Instructions\n\n" + "\n".join(entries) + "\n"
    LATEST_FILE.write_text(content, encoding="utf-8")


def main() -> None:
    # Skip when Bucky spawned this Claude Code session (loop prevention)
    if os.environ.get("BUCKY_SUBPROCESS") == "1":
        return

    hook_event = os.environ.get("CLAUDE_HOOK_EVENT", "")

    try:
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}

    record: dict = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "event": hook_event,
        "session_id": data.get("session_id", ""),
        "cwd": os.getcwd(),
    }

    if hook_event == "UserPromptSubmit":
        prompt = data.get("prompt", "")
        if not prompt:
            return
        record["source"] = "claudecode"
        record["prompt_preview"] = prompt[:400]

    elif hook_event == "PostToolUse":
        tool_name = data.get("tool_name", "")
        if "codex" not in tool_name.lower():
            return
        record["source"] = "codex"
        record["tool"] = tool_name
        inp = data.get("tool_input", {})
        record["input_preview"] = json.dumps(inp, ensure_ascii=False)[:400] if inp else ""

    else:
        return

    AWARENESS_DIR.mkdir(parents=True, exist_ok=True)

    log_file = AWARENESS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    _update_latest(record)


if __name__ == "__main__":
    main()
