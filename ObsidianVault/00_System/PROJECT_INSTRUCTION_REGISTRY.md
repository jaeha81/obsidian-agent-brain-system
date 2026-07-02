---
type: registry
title: Project Instruction Registry
status: active
created: 2026-07-03
---

# Project Instruction Registry

Tracks the instruction-authority files that govern this project, so Charlie (and humans) can
tell at a glance whether they exist and how stale they are. This registry does not duplicate
their content — it points at them.

## Format

```
### <file>
- path: <repo-relative path>
- scope: <what it governs>
- supersedes: <what it replaces, if anything>
```

## Entries

### AGENTS.md
- path: `AGENTS.md`
- scope: Top-level instruction file for agentic coding tools operating on this repo.
- supersedes: n/a

### CLAUDE.md
- path: `CLAUDE.md`
- scope: Claude Code-specific operating rules — commit/push approval policy, storage
  boundaries, Bucky/Codex/Claude Code role split.
- supersedes: n/a (project-level; inherits the user's global
  `C:\Users\<user>\.claude\CLAUDE.md`)

### USER_OPERATING_INTENT.md
- path: `ObsidianVault/00_System/USER_OPERATING_INTENT.md`
- scope: Top-level user goal, so small tasks cannot silently replace it.
- supersedes: n/a

### OPERATING_INTENT.md
- path: `OPERATING_INTENT.md` (repo root, if present)
- scope: Repo-root operating intent reference used by `bucky_os_gate.py`'s legacy checks.
- supersedes: n/a — note: as of 2026-07-03 this file was not confirmed present at repo root;
  `USER_OPERATING_INTENT.md` above is the current authority. Charlie will report this
  mismatch in `authority_files` if it remains missing.
