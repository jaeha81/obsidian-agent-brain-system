---
type: registry
title: Charlie Change Log
status: active
created: 2026-07-03
---

# Charlie Change Log

A risk- and approval-centered log of system-level changes (not a full commit log — `git log`
already has that). An entry goes here when a change touched something Charlie audits:
authority files, registries, git hooks, `.env` runtime config, or the audit system itself.

## Format

```
### YYYY-MM-DD — <one-line summary>
- risk: P1 | P2 | P3
- approval: <how the user approved this — quote or describe>
- changed: <files/areas touched>
- verification: <how it was confirmed to work>
```

## Entries

### 2026-07-03 — Bring Charlie audit system online (Tasks 1–3 of the 2026-06-15 plan)
- risk: P3
- approval: User asked to make the previously-unimplemented Charlie/channel work "실질적으로
  진행" instead of staying a report-only finding.
- changed: `ObsidianVault/03_Projects/agents/charlie.md`,
  `ObsidianVault/00_System/USER_OPERATING_INTENT.md`,
  `ObsidianVault/00_System/CHARLIE_ERROR_REGISTRY.md` (this file's sibling),
  `ObsidianVault/00_System/PROJECT_INSTRUCTION_REGISTRY.md`, `scripts/charlie_audit.py`.
- verification: `python -m py_compile scripts/charlie_audit.py`,
  `python scripts/charlie_audit.py`, `Test-Path docs/data/charlie_status.json`,
  `git diff --stat` (confirms the script itself made no commit/push).

### 2026-07-02 — Remove auto git-push hook from sync_system_enhance.py
- risk: P1
- approval: User approved via handoff `2026-07-02-bucky-git-deploy-fix.md` (Phase 2, "A안,
  이미 승인됨"), then explicitly re-confirmed in-session before each push.
- changed: `scripts/sync_system_enhance.py` (dev clone commit `803cf3e`, runtime-folder mirror
  commit `56899ac`), `.claude/settings.json` (`PostToolUse` hook removed, user-approved).
- verification: `Select-String -Pattern "subprocess|git_push|run_git"` on the file returns no
  matches; git reflog confirms no further auto-push after the fix.

### 2026-07-03 — Correct/clean up Discord channel config
- risk: P2
- approval: User approved per-item via AskUserQuestion (chsh-mining ID fix: yes;
  channel recreation: no; `.env` cleanup: yes).
- changed: `.env` (`JH_CHSH_MINING_CHANNEL_ID` corrected, `JH_TASKBOARD_CHANNEL_ID` and
  `JH_KMONG_CHANNEL_ID` cleared, dead ID removed from `DISCORD_CHANNEL_IDS`).
- verification: Discord REST API channel checks re-run after each bot restart; bot log shows
  `Bot ready` and the reduced, correct watch-channel set.
