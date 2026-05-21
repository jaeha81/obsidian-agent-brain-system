#!/usr/bin/env python3
"""
Claude Code Session End Protocol — automates session close steps.

1. Removes lock files from 00_System/LOCKS/
2. Updates AGENT_STATE.md (current_task → none, status → standby)
3. Writes session report to 10_AgentBus/reports/ClaudeCode/
4. Appends entry to HANDOFF_LOG.md

Usage:
    python scripts/session_end.py \\
        --agent ClaudeCode \\
        --task "Phase 6 Agent Worker Flow" \\
        --result "완료" \\
        --notes "optional notes"
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
VAULT = ROOT / "ObsidianVault"
SYSTEM = VAULT / "00_System"
LOCKS_DIR = SYSTEM / "LOCKS"
AGENTBUS = VAULT / "10_AgentBus"


def clear_locks(agent: str) -> list[str]:
    if not LOCKS_DIR.exists():
        return []
    removed = []
    for lock in LOCKS_DIR.glob(f"LOCK_{agent}_*"):
        lock.unlink()
        removed.append(lock.name)
    return removed


def update_agent_state(agent: str, task_result: str):
    state_file = SYSTEM / "AGENT_STATE.md"
    if not state_file.exists():
        return
    text = state_file.read_text(encoding="utf-8")
    escaped = re.escape(agent)
    text = re.sub(
        rf"(### {escaped}.*?- status:) \S+",
        r"\1 standby",
        text, flags=re.DOTALL
    )
    text = re.sub(
        rf"(### {escaped}.*?- current_task:) .+",
        lambda m: m.group(1) + " 없음 — " + task_result,
        text, flags=re.DOTALL
    )
    state_file.write_text(text, encoding="utf-8")


def write_report(agent: str, task: str, result: str, notes: str) -> Path:
    now = datetime.now()
    ts = now.strftime("%Y%m%d_%H%M%S")
    iso = now.isoformat(timespec="seconds")

    report_dir = AGENTBUS / "reports" / agent
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{ts}_session_report.md"

    content = f"""---
type: session_report
agent: {agent}
task: {task}
result: {result}
created: {iso}
---

## Session Report

| 항목 | 내용 |
|------|------|
| Agent | {agent} |
| Task | {task} |
| Result | {result} |
| Date | {iso} |

## Notes

{notes or "없음"}
"""
    report_path.write_text(content, encoding="utf-8")
    return report_path


def append_handoff(agent: str, task: str, result: str, notes: str):
    handoff_file = SYSTEM / "HANDOFF_LOG.md"
    if not handoff_file.exists():
        return
    iso = datetime.now().isoformat(timespec="seconds")
    entry = f"\n## [{iso}] {agent} — {task}\n\n- Result: {result}\n- Notes: {notes or '없음'}\n"
    with handoff_file.open("a", encoding="utf-8") as f:
        f.write(entry)


def main():
    parser = argparse.ArgumentParser(description="Claude Code Session End Protocol")
    parser.add_argument("--agent", default="ClaudeCode", help="Agent name (default: ClaudeCode)")
    parser.add_argument("--task", required=True, help="Task description")
    parser.add_argument("--result", default="완료", help="Result summary")
    parser.add_argument("--notes", default="", help="Additional notes")
    args = parser.parse_args()

    if not re.match(r'^[A-Za-z0-9_-]+$', args.agent):
        print(f"ERROR: --agent must match [A-Za-z0-9_-]+: {args.agent!r}", file=sys.stderr)
        sys.exit(1)

    removed = clear_locks(args.agent)
    if removed:
        print(f"Locks cleared: {removed}")

    update_agent_state(args.agent, args.result)
    print(f"AGENT_STATE.md updated: {args.agent} → standby")

    report_path = write_report(args.agent, args.task, args.result, args.notes)
    print(f"Report written: {report_path}")

    append_handoff(args.agent, args.task, args.result, args.notes)
    print(f"HANDOFF_LOG.md updated")


if __name__ == "__main__":
    main()
