---
type: recovery_status
priority: P1
status: stabilized
from: Codex
created: 2026-05-31T18:50:00+09:00
related:
  - 20260531_162046_c_drive_cleanup_incident_notice.md
  - C: drive cleanup recovery
  - Discord Bucky bot
  - Codex Playwright runtime
tags:
  - #area/ai_automation
---

# C: Drive Cleanup Recovery Status

## Summary

Codex performed recovery work after the C: drive cleanup disrupted runtime dependencies and exposed Bucky bot restart fragility. No additional cleanup/deletion should be performed during this recovery window.

## Restored / Verified

- Codex Playwright runtime:
  - Restored missing `playwright-core` junction in the Codex bundled Node runtime.
  - Reinstalled Playwright Chromium/headless shell/ffmpeg under `C:\Users\user1\AppData\Local\ms-playwright`.
  - Verified Chromium launches successfully outside the Codex sandbox.

- Node/npm/pnpm/pip:
  - `npm cache verify` passes under user permissions.
  - `pnpm store path` and `pnpm store status` pass under user permissions.
  - `python -m pip cache info` works and cache directories exist.

- Claude/Codex CLI:
  - `codex --version` works outside sandbox.
  - `claude --version` works.
  - Node and Python version checks work.

- Claude Code global instruction sync:
  - Ran `scripts\sync_claude_instructions.py`.
  - Backup created under `C:\Users\user1\.claude\backups`.
  - `scripts\sync_claude_instructions.py --check` now reports current.

- Discord Bucky bot:
  - Current watchdog process: python PID `48364`.
  - Current bot process: python PID `50004`.
  - PID file now points to `50004`.
  - Bot logs show Discord Gateway connected, `Bot ready: ObsidianAgentBot#3738`, WorkerPool registered, CodexPoller started.
  - After a 35-second wait, both watchdog and bot PIDs were still alive/responding.

- Obsidian/Bucky checks:
  - `python scripts\bucky_os_gate.py --fast` passes: 5/5.
  - `python scripts\preflight_check.py` shows core operational checks OK:
    - `vault_path: ok`
    - `env_file: ok`
    - `git_sync: ok`
    - `claude_md: ok`
    - `bucky_os_gate: ok 19 checks`
    - `claude_command: ok`
    - `codex_command: ok`

## Remaining Warnings

- `preflight_check.py` still exits with warning status because:
  - Worktree has existing modified/untracked files.
  - `git_fetch` cannot reach GitHub through `127.0.0.1` proxy at the time of verification.

- Do not treat these warning lines as proof that the cleanup recovery failed. The substantive local runtime checks are green.

## Important Guardrails

- Do not delete more caches, Docker data, WSL data, Claude VM data, Android emulator data, or `node_modules` as part of this recovery.
- Do not expose `.env` or token values in logs/reports.
- If Bucky bot fails again, inspect the current watchdog logs under `.logs` and the PID file before starting another instance.
- Avoid duplicate bot starts. Verify command lines for `discord_bot.py`, `discord_bot_watchdog.py`, and `bucky_bot_supervisor.py` first.
