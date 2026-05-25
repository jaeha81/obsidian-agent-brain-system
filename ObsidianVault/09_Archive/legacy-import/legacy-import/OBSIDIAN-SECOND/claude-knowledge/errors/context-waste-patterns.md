# Context Waste Patterns

> Created from 2026-05-16 session-state sync. Source PC: home PC (user1).

## Repeated Waste Patterns

1. Reading the full global instruction file during sync when `session-state.md` is sufficient.
2. Re-reading files already summarized by the user or by the current session.
3. Exploring an empty or unknown project before confirming the user's goal and source path.
4. Searching broad logs such as Agent Room JSONL before narrowing by date, speaker, status, or keyword.
5. Treating Google Drive sync folders as git repositories instead of using them as shared state/doc storage.

## Rule

Prefer a narrow pointer first: `session-state.md`, exact daily report, exact handoff, then targeted grep/search. Expand only when the next action is still ambiguous.
