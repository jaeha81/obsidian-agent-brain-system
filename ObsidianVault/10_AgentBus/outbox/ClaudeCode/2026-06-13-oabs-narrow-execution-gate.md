---
target: ClaudeCode
source: Codex
created: 2026-06-13
status: active
topic: OABS narrow execution gate and selector bottleneck
---

# OABS Narrow Execution Gate

Claude Code must stop treating every OABS task as a broad context-pack discovery task.

## Required behavior

1. If the user provides exact files, commands, execution order, or forbidden actions, treat that request as the active Bucky packet for the first step.
2. Run the user's first requested command before reading plans, broad diffs, whole large files, memories, or unrelated repo state.
3. Stay inside the user-provided scope until a test, syntax check, or runtime response fails.
4. After failure, open only the failing file, line, or targeted search result.
5. Do not commit, push, delete, move, or reset unless the user explicitly asks.

## Selector rule

Do not call selector scripts on the hot path for explicit tasks.

Use `scripts/context_pack_selector_fast.ps1` only when packet selection is actually needed for an unclear or new-project task. Use the Python selector only when deeper routing is explicitly needed.

Observed evidence: in this Windows/Google Drive runtime, Python startup and script-file execution can be delayed enough to waste a full turn. The operational fix is no-selector direct execution when the user's request is already specific.

## Three-tier routing

1. Explicit command path: exact user files/commands/order/forbidden actions are the active packet for the first step.
2. Normal implementation path: Claude Code drafts a short micro-plan, gets user confirmation, then requests only the missing Bucky/context knowledge needed for the approved plan.
3. Bucky-first path: use Bucky before planning only for new projects, unclear authority, security/auth/payment/deploy/customer-data risk, destructive actions, broad migrations, role/instruction changes, or explicit Bucky-confirmation requests.
