---
type: incident_notice
priority: P1
status: active-recovery-context
from: Codex
created: 2026-05-31T16:21:23+09:00
related:
  - C: drive cleanup
  - Discord Bucky bot outage
  - Codex Playwright runtime recovery
  - Obsidian Agent Brain System runtime
tags:
  - #area/ai_automation
---

# C: Drive Cleanup Incident Notice

## Summary

On 2026-05-31, Codex performed C: drive cleanup to recover disk space. The cleanup was intended to remove regenerable caches only, but it caused or exposed runtime issues for Codex/Claude Code/Obsidian Agent Brain System operations.

This note is for Claude Code and Codex recovery work. Do not assume the G: repo contents were intentionally deleted. The observed impact is runtime/cache/process-state related.

## Cleanup Actions Performed

Deleted/regenerated cache targets on C:

- `C:\Users\user1\AppData\Local\npm-cache`
- `C:\Users\user1\AppData\Local\Temp` contents
- `C:\Users\user1\AppData\Local\ms-playwright`
- `C:\Users\user1\AppData\Local\Ollama\updates_v2`
- `C:\Users\user1\AppData\Local\pip\Cache`
- `C:\Users\user1\AppData\Local\pnpm-cache`

Initial recovered space was about 16.84 GB. No intentional deletion was performed inside `G:\내 드라이브\obsidian-agent-brain-system`.

## Confirmed Runtime Effects

1. Codex Playwright path broke after `ms-playwright` deletion.
   - Symptom: `require('playwright')` failed first due to missing `playwright-core` link.
   - Fix applied: restored `playwright-core` junction under Codex bundled Node runtime.
   - Then Chromium executable was missing.
   - Fix applied: reinstalled Playwright Chromium/headless shell/ffmpeg via Codex bundled Playwright CLI.
   - Verified: Playwright Chromium launches successfully outside sandbox.

2. Discord Bucky bot was not running.
   - Stale PID file existed: `ObsidianVault\10_AgentBus\signals\bucky_bot.pid` pointed to a dead process.
   - Last previous Discord resume log was around 2026-05-31 10:02.
   - Restart attempted via `start_discord_bot.bat`.
   - Current verified bot process after restart: python PID `71788`.
   - Log evidence after restart: Discord Gateway connected, `Bot ready: ObsidianAgentBot#3738`, WorkerPool registered, CodexPoller started.

3. Supervisor reliability risk found.
   - `scripts\bucky_bot_supervisor.py` has an observed `UnboundLocalError` involving `_restart_count` in the restart path.
   - This can make the supervisor die when the bot exits instead of reliably restarting it.
   - This was observed in `supervisor_autostart.log`.

## Current Guidance For Claude Code / Codex

- Treat this as a runtime recovery incident, not a normal feature task.
- Do not commit/push unless the user explicitly asks.
- Do not delete more caches or clean Docker/WSL/Claude VM/Android data during recovery.
- Check live state before changing code:
  - `discord_bot.err`
  - `bucky_restart.out.log`
  - `ObsidianVault\10_AgentBus\signals\bucky_bot.pid`
  - actual PID liveness for the bot process
- If repairing supervisor code, focus narrowly on the restart-loop bug and stale PID handling.
- If browser automation fails, first verify Playwright under Codex bundled runtime and `C:\Users\user1\AppData\Local\ms-playwright`.
- Avoid exposing `.env` secret values in reports.

## Known Good Checks After Recovery

- `codex --version` works outside sandbox.
- `claude --version` works.
- Node/npm/python version checks work.
- Playwright Chromium launch works outside sandbox.
- Discord Bucky bot reconnected and is running as PID `71788` at the time this notice was written.

## User Context

The user asked Claude to perform recovery and asked Codex to notify Claude Code/Codex that the C: drive cleanup likely caused the current abnormal behavior. This file is that handoff notice.
