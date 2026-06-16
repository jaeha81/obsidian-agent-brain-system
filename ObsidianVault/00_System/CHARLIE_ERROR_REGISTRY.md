---
type: charlie-error-registry
status: active
created: 2026-06-15
---

# Charlie Error Registry

This registry records system-level errors and recurrence rules for the Obsidian Brain System.

## Error Format

| ID | Date | Severity | Area | Symptom | Cause | Evidence | Status | Recurrence Rule |
|---|---|---|---|---|---|---|---|---|
| CH-0001 | 2026-06-15 | P2 | instructions | Completed AgentBus gates were still described as pending in Bucky context | Stale authority text remained in `BUCKY_CONTEXT.md` | `session-state.md` gate table vs `BUCKY_CONTEXT.md` section 9 | mitigated | Gate status must be checked against `session-state.md` before briefing |
| CH-0002 | 2026-06-15 | P1 | shared-agent-degradation | Bucky, Codex, and Claude Code risk becoming ineffective together | User intent, Bucky context, local project instructions, and small-task momentum can conflict | Active user report during Charlie setup | active | If multiple agents lose top-level intent, return to `USER_OPERATING_INTENT.md` before continuing work |
| CH-0003 | 2026-06-16 | P2 | turn-continuity | Codex repeatedly reported status but omitted the next work directive requested by the user | The active request queue was not treated as a report closure condition inside the same session | User corrections in current Charlie continuation session | active | Every non-trivial report must close with completed/open/next directive/do-not-do-without-approval |

## Severity

- P1: data loss, security, destructive action, uncontrolled runtime loop
- P2: authority conflict, stale state, role invasion, repeated task drift
- P3: clarity, style, missing documentation, low-risk cleanup

## Repeat Pattern Rule

When the same symptom appears twice, Charlie reports it as `[반복 패턴 경보]` and proposes a prevention rule.
