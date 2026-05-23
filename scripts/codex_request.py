#!/usr/bin/env python3
"""
Codex Review Request — writes a review task to 10_AgentBus/outbox/Hermes/
so Codex can pick it up and review independently.

Usage:
    python scripts/codex_request.py \\
        --task-id TASK_001 \\
        --subject "legalize_mcp_server.py 코드 리뷰" \\
        --files "scripts/legalize_mcp_server.py,scripts/agentbus_graphify_bridge.py" \\
        --priority P2
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env", encoding="utf-8", override=True)

_VALID_TASK_ID = re.compile(r'^[A-Za-z0-9_-]{1,32}$')
_MAX_CONTEXT_CHARS = 4000
_GRAPH_JSON_PATTERN = re.compile(r'"nodes"\s*:\s*\[|"edges"\s*:\s*\[')
VAULT = ROOT / "ObsidianVault"
WORKER_NAME = os.getenv("AGENTBUS_WORKER_NAME", "Hermes")
OUTBOX_WORKER = VAULT / "10_AgentBus" / "outbox" / WORKER_NAME


def write_request(task_id: str, subject: str, files: list[str], priority: str, context: str) -> Path:
    now = datetime.now()
    ts = now.strftime("%Y%m%d_%H%M%S")
    iso = now.isoformat(timespec="seconds")

    OUTBOX_WORKER.mkdir(parents=True, exist_ok=True)
    out_path = OUTBOX_WORKER / f"{priority}_{ts}_Codex_{task_id}.md"

    file_list = "\n".join(f"- `{f}`" for f in files)
    content = f"""---
type: review_request
task_id: {task_id}
from: {WORKER_NAME}
to: Codex
priority: {priority}
status: pending
created: {iso}
---

# Task: {task_id}
- From: {WORKER_NAME}
- To: Codex
- Priority: {priority}
- Date: {iso}
- Status: pending

## Request

{subject}

## Files to Review

{file_list}

## Context

{context or "없음"}

## Expected Output

`10_AgentBus/outbox/Codex/{task_id}_review.md` 형식으로 리뷰 결과 저장.
"""
    out_path.write_text(content, encoding="utf-8")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Request Codex review via AgentBus")
    parser.add_argument("--task-id", required=True, help="Unique task ID (e.g. TASK_001)")
    parser.add_argument("--subject", required=True, help="Review subject description")
    parser.add_argument("--files", default="", help="Comma-separated file paths to review")
    parser.add_argument("--priority", default="P2", choices=["P0", "P1", "P2"], help="Priority (default: P2)")
    parser.add_argument("--context", default="", help="Additional context for Codex")
    args = parser.parse_args()

    if not _VALID_TASK_ID.match(args.task_id):
        print(f"ERROR: task_id must match [A-Za-z0-9_-]{{1,32}}: {args.task_id!r}", file=sys.stderr)
        sys.exit(1)
    if len(args.context) > _MAX_CONTEXT_CHARS:
        print(f"ERROR: context too large ({len(args.context)} chars, max {_MAX_CONTEXT_CHARS})", file=sys.stderr)
        sys.exit(1)
    if _GRAPH_JSON_PATTERN.search(args.context):
        print("ERROR: context appears to contain graph.json content — this is prohibited", file=sys.stderr)
        sys.exit(1)

    files = [f.strip() for f in args.files.split(",") if f.strip()]
    out_path = write_request(args.task_id, args.subject, files, args.priority, args.context)
    print(f"Codex review request written: {out_path}")


if __name__ == "__main__":
    main()
