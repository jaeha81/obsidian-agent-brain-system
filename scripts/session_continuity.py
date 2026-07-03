#!/usr/bin/env python3
"""Durable session continuation helper for Bucky-managed work.

This writes a compact handoff node instead of relying on chat compression.
It also emits the numbered user question Bucky should ask before continuing
unfinished work in the next conversation.
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "ObsidianVault"
SYSTEM = VAULT / "00_System"
HANDOFFS = VAULT / "10_AgentBus" / "handoffs"
NEXT_HANDOFF = SYSTEM / "CHARLIE_NEXT_SESSION_HANDOFF.md"


def _slug(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9가-힣_-]+", "-", text.strip()).strip("-")
    return cleaned[:60] or "session-continuity"


def _bullets(items: list[str], fallback: str = "None") -> str:
    if not items:
        return f"- {fallback}"
    return "\n".join(f"- {item}" for item in items)


def numbered_pending_prompt(pending: list[str]) -> str:
    if not pending:
        return "미완료 항목 없음. 다음 작업 지시를 주세요."
    lines = ["미완료 항목이 남아 있습니다. 진행할 번호를 선택해 주세요:"]
    lines.extend(f"{idx}. {item}" for idx, item in enumerate(pending, 1))
    lines.append("0. 지금은 진행하지 않음")
    return "\n".join(lines)


def build_handoff(
    *,
    agent: str,
    request: str,
    completed: list[str],
    pending: list[str],
    blockers: list[str],
    next_read: list[str],
    notes: str,
    created: datetime,
) -> str:
    prompt = numbered_pending_prompt(pending)
    return f"""---
type: session_continuity_handoff
agent: {agent}
created: {created.isoformat(timespec="seconds")}
status: active
---

# Session Continuity Handoff

## User Request Context

{request}

## Completed

{_bullets(completed)}

## Unfinished Queue

{_bullets(pending)}

## Blockers

{_bullets(blockers)}

## Next Session Reading Order

{_bullets(next_read or [
    "OPERATING_INTENT.md",
    "ObsidianVault/00_System/USER_OPERATING_INTENT.md",
    "ObsidianVault/00_System/CHARLIE_NEXT_SESSION_HANDOFF.md",
])}

## Do Not Compress

- Do not rely on chat compression as the transfer mechanism.
- Preserve this handoff path and ask the numbered unfinished-work question before continuing.
- Do not collapse user corrections into a generic summary; keep the before/after request context visible.

## User Question For Next Turn

```text
{prompt}
```

## Notes

{notes or "None"}
"""


def write_handoff(
    *,
    agent: str,
    request: str,
    completed: list[str],
    pending: list[str],
    blockers: list[str],
    next_read: list[str],
    notes: str,
    now: datetime | None = None,
) -> Path:
    created = now or datetime.now()
    HANDOFFS.mkdir(parents=True, exist_ok=True)
    filename = f"{created.strftime('%Y%m%d_%H%M%S')}_{_slug(agent)}_session_continuity.md"
    path = HANDOFFS / filename
    content = build_handoff(
        agent=agent,
        request=request,
        completed=completed,
        pending=pending,
        blockers=blockers,
        next_read=next_read,
        notes=notes,
        created=created,
    )
    path.write_text(content, encoding="utf-8")
    NEXT_HANDOFF.write_text(content, encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Write a durable next-session handoff.")
    parser.add_argument("--agent", default="Bucky")
    parser.add_argument("--request", required=True)
    parser.add_argument("--completed", action="append", default=[])
    parser.add_argument("--pending", action="append", default=[])
    parser.add_argument("--blocker", action="append", default=[])
    parser.add_argument("--next-read", action="append", default=[])
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    path = write_handoff(
        agent=args.agent,
        request=args.request,
        completed=args.completed,
        pending=args.pending,
        blockers=args.blocker,
        next_read=args.next_read,
        notes=args.notes,
    )
    print(f"handoff: {path}")
    print(numbered_pending_prompt(args.pending))


if __name__ == "__main__":
    main()
