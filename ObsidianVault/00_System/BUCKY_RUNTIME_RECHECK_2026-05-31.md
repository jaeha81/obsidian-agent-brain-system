---
type: runtime-recheck
owner: Bucky
agent: Codex
created: 2026-05-31
status: active-recovery-context
priority: P1
---

# Bucky Runtime Recheck — 2026-05-31

## Purpose

This note keeps the C: drive cleanup incident and the Bucky Agent OS recheck visible at the next session entry point. It is a compact pointer note. Use the referenced files for details instead of pasting long incident text into Claude Code or Codex prompts.

## Required First Reads

1. `ObsidianVault/00_System/session-state.md`
2. `ObsidianVault/10_AgentBus/handoffs/20260531_162046_c_drive_cleanup_incident_notice.md`
3. `ObsidianVault/00_System/ROUTING_RULES.md`
4. `ObsidianVault/05_Frameworks/guides/context-management-strategy.md`

## Incident Summary

- C: cleanup removed regenerable caches, including `ms-playwright`.
- The incident notice records about 16.84 GB reclaimed.
- No intentional deletion was performed inside `G:\내 드라이브\obsidian-agent-brain-system`.
- Codex Playwright runtime broke after cache deletion and was recovered.
- Discord Bucky bot was stale/dead, then restarted; incident note recorded PID `71788` at that time.
- Current recheck found PID `71788` was no longer live and `discord_bot.py` was running as PID `50004`; `ObsidianVault/10_AgentBus/signals/bucky_bot.pid` was updated to `50004`.
- Do not expose `.env` values in status reports.
- Do not perform additional Docker, WSL, Claude VM, Android, or broad cache cleanup during this recovery.

## Recheck Findings

| Area | Current Finding | Action |
|---|---|---|
| Instruction authority | `preflight_check.py` reported `bucky_os_gate: ok 19 checks`; fast gate reported `ok 5/5`. | Keep using Bucky packets and selector before new project work. |
| Session continuity | `session-state.md` was stale at 2026-05-30 and did not point to the 2026-05-31 incident. | Updated this session to point at the incident and this recheck note. |
| Context pressure | `context_warning.py` exists and documents 50/75/90 percent behavior, but app-level hook enforcement is not proven. | Treat compression as unsafe; write handoff and start a new session when context is heavy. |
| AgentBus records | Incident notice exists in handoffs plus Codex and ClaudeCode outboxes. | Agents should reference those paths, not paste the full incident. |
| Supervisor restart | `scripts/bucky_bot_supervisor.py` used `_restart_count += 1` inside `run()` without a global declaration. | Codex fixed the scoping bug on 2026-05-31. |
| Bucky bot process | `discord_bot_watchdog.py` is currently running as PID `48364`; `discord_bot.py` is currently running as PID `50004`. | Keep PID file aligned and avoid duplicate bot starts. |
| Full gate report | Direct full gate can fail while writing its default report file under Google Drive. | If full gate report write fails, report the exact error and run the fast gate plus preflight. |

## Operating Rules Until Cleared

1. For any new project or folder, get a Bucky project packet first.
2. For long work, write an AgentBus or session handoff before context pressure forces compression.
3. Claude Code implements; Codex reviews independently unless the user explicitly asks Codex to edit.
4. Store durable state in Vault/AgentBus files and pass paths between agents.
5. No commit, push, destructive cleanup, or secret-value reporting without explicit user approval.

## Codex Session Fallback

Codex app-level PreCompact or equivalent hook enforcement has not been verified. Until that is proven, Codex must treat manual handoff as the active operating rule:

1. When context grows heavy, do not continue by compression.
2. Run `scripts/codex_session_handoff.py` manually.
3. Save the handoff under `ObsidianVault/10_AgentBus/handoffs/Codex/`.
4. Start a new Codex session from that handoff and only the referenced files.
5. Keep Codex hook or automation integration as a separate verification task.

## Verification Commands

```powershell
python -X utf8 scripts\bucky_os_gate.py --fast --fail-on-error
python -X utf8 scripts\preflight_check.py
python -c "import ast, pathlib; files=['scripts/bucky_bot_supervisor.py','scripts/discord_bot.py','scripts/task_queue.py']; [ast.parse(pathlib.Path(f).read_text(encoding='utf-8'), filename=f) for f in files]; print('syntax_ok')"
```

## Next Manual Checks

- Confirm whether Claude Code's actual settings hook invokes `scripts/context_warning.py`.
- Confirm whether Codex app has an equivalent enforced handoff path or only manual `scripts/codex_session_handoff.py`.
- Recheck Bucky bot PID liveness outside the sandbox if PID status is uncertain.

*Related: [[bucky-system-hub]]*

