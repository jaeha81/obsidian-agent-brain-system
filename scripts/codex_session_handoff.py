#!/usr/bin/env python3
"""Create a Codex next-session handoff without compressing the current session."""

from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env", encoding="utf-8-sig", override=True)

VAULT = Path(os.getenv("VAULT_PATH", str(ROOT / "ObsidianVault")))
HANDOFF_DIR = VAULT / "10_AgentBus" / "handoffs" / "Codex"


def ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def split_files(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def write_handoff(task_id: str, summary: str, remaining: str, files: list[str], reason: str) -> Path:
    HANDOFF_DIR.mkdir(parents=True, exist_ok=True)
    path = HANDOFF_DIR / f"{ts()}_{task_id}_manual_handoff.md"
    file_list = "\n".join(f"- `{file}`" for file in files) or "- None listed"
    path.write_text(
        f"""---
type: codex_manual_handoff
task_id: {task_id}
created: {iso()}
status: next_session_required
reason: {reason}
---

# Codex Manual Handoff: {task_id}

## Why

Do not compress the current Codex session to continue. Use this handoff to start a clean next session.

## Summary So Far

{summary}

## Files / Areas

{file_list}

## Remaining Work

{remaining}

## Next Session Checklist

1. Run `python scripts/preflight_check.py`.
2. Run `git status --short`.
3. Read this handoff only, then inspect listed files.
4. Continue with the normal Codex review report format.
""",
        encoding="utf-8",
    )
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Codex next-session handoff.")
    parser.add_argument("--task-id", required=True, help="Short task id, e.g. CODEX_CTX_001")
    parser.add_argument("--summary", required=True, help="What is already known or done")
    parser.add_argument("--remaining", required=True, help="What next session must do")
    parser.add_argument("--files", default="", help="Comma-separated files or folders")
    parser.add_argument("--reason", default="context_guard", help="Handoff reason")
    args = parser.parse_args()

    path = write_handoff(
        args.task_id,
        args.summary,
        args.remaining,
        split_files(args.files),
        args.reason,
    )
    print(f"Codex handoff written: {path}")


if __name__ == "__main__":
    main()
