---
type: charlie-next-session-handoff
status: active
created: 2026-06-15
owner: Charlie
---

# Charlie Next Session Handoff

This file exists because the user repeatedly warned that long sessions, context bloat, and compression cause Bucky, Codex, and Claude Code to forget the real mission.

## Why The Next Session Should Continue From Here

The current session established Charlie as a gradual, independent system audit layer for the Obsidian Brain System. The work is not complete, but the core authority and guardrail files now exist.

The next session must not restart from generic Bucky routing or treat the latest small task as the whole mission.

## User's Top-Level Intent

The Obsidian Brain System exists for:

1. Efficient AI use
2. Stronger memory across sessions
3. Efficient context management
4. User feedback driven evolution
5. Daily Plus and GPT conversation capture
6. Obsidian knowledge-base strengthening
7. Selective retrieval through LLM Wiki, Graphify, Context Packs, and exact references

If these functions are not working, the system is failing its reason for existing.

## Current Charlie Role

Charlie is the independent system audit agent.

Charlie must:

- Audit Bucky, Codex, Claude Code, Discord, Daily Plus, dashboards, and project instructions.
- Preserve user intent and prevent shared degradation.
- Record errors and recurrence rules.
- Protect the Daily Plus/GPT to Obsidian knowledge loop.
- Avoid continuous token usage.
- Avoid automatic fixes unless the user approves.

Charlie must not:

- Replace Bucky as work orchestrator.
- Direct Claude Code unnecessarily.
- Create ping-pong between agents.
- Read the whole knowledge base when targeted retrieval is enough.
- Continue a bloated session without a handoff.

## Files Created Or Updated In This Session

Read these first in the next session:

1. `OPERATING_INTENT.md`
2. `ObsidianVault/00_System/USER_OPERATING_INTENT.md`
3. `ObsidianVault/03_Projects/agents/charlie.md`
4. `ObsidianVault/00_System/CHARLIE_AGENT_COORDINATION.md`
5. `ObsidianVault/00_System/CHARLIE_ERROR_REGISTRY.md`
6. `ObsidianVault/00_System/CHARLIE_CHANGE_LOG.md`
7. `ObsidianVault/00_System/PROJECT_INSTRUCTION_REGISTRY.md`
8. `scripts/charlie_audit.py`
9. `docs/charlie-system-audit.html`
10. `docs/superpowers/plans/2026-06-15-charlie-system-audit.md`

## Current Verified State

- `scripts/charlie_audit.py` syntax check passed with `python -B`.
- `python -B scripts\charlie_audit.py --no-write` runs.
- Current Charlie state is `WARNING`.
- The remaining confirmed warning is the large dirty worktree.
- The dirty worktree is now classified by Charlie, not vague:
  - `bucky-discord-daily-plus`: 58
  - `charlie`: 15
  - `support-tooling`: 17
  - `knowledge-vault`: 14
  - `google-revenue-dashboard`: 8
  - `kmong`: 6
  - `local-review-artifact`: 2
- Dirty count was reduced from 127 to 120 by ignoring local runtime artifacts only; no delete/reset/commit was done.
- Hardcoded collab admin password was removed from `scripts/bucky_chat_server.py`.
- `scripts/charlie_audit.py` now detects hardcoded secret-like assignments and reports worktree areas.
- UTF-8 BOM pollution was removed from Python scripts.
- Broken Korean dashboard/test channel labels were restored and verified in Codex in-app browser.
- Targeted tests passed: `python -B -m unittest tests.test_daily_plus_channel_bridge tests.test_dashboard_intake_payloads tests.test_intake_channel_allowed`.
- Writing `docs/data/charlie_status.json` and `data/charlie/charlie_status.json` failed with permission denied in this environment.
- The dashboard has a bootstrap display so it can still communicate Charlie's intent without JSON.

## Do Not Repeat

- Do not send every decision through Claude Code and then back to Codex.
- Do not let Bucky context override `USER_OPERATING_INTENT.md`.
- Do not treat a small file edit as completing the larger system restoration.
- Do not load the whole Obsidian knowledge base just because the content is important.
- Do not continue a context-heavy session without explaining why a new session is needed.
- Do not let user feedback disappear without writing it into durable instructions or registries.

## Next Session First Actions

1. Read `OPERATING_INTENT.md`.
2. Read this file.
3. Read `ObsidianVault/00_System/USER_OPERATING_INTENT.md`.
4. Read `ObsidianVault/03_Projects/agents/charlie.md`.
5. Run `python -B scripts\charlie_audit.py --no-write --json`.
6. Do not reclassify from scratch. Use `git_status.by_area` from Charlie output as the working queue.
7. Start with `bucky-discord-daily-plus` because it is the largest and most central OABS recovery group.
8. If speed matters, use parallel agents only for independent read-only classification:
   - Agent A: `bucky-discord-daily-plus` preserve vs verify vs risky.
   - Agent B: `support-tooling` and `knowledge-vault` preserve vs artifact.
   - Agent C: `google-revenue-dashboard` and `kmong` readiness.
   Main Codex keeps authority decisions, file edits, verification, and user reporting.

## Next Planned Work

1. Reduce `bucky-discord-daily-plus=58` into:
   - preserve now
   - needs runtime/browser verification
   - needs user approval
   - likely artifact/noise
2. Then reduce `support-tooling=17` and `knowledge-vault=14`.
3. Keep Charlie files as a coherent recovery packet unless the user rejects Charlie.
4. Do not remove Google revenue or Kmong files without user approval; classify readiness only.
5. Re-run targeted tests and Codex in-app browser preview after dashboard edits.
6. Investigate the status JSON write permission issue without forcing a workaround.

## Speed Rules For Next Session

- No context selector first. The user gave the packet and this handoff is the active queue.
- Do not reread the whole Vault.
- Do not spend turns explaining the dirty worktree from scratch.
- Use `python -B scripts\charlie_audit.py --no-write --json` as the state source.
- Use `git diff --stat` and targeted `git diff -- <files>` only.
- If agents are available, dispatch read-only classification agents; do not let agents edit files.
- Main Codex must keep the active queue visible until all user-requested categories are handled, deferred, or blocked.

## User Reminder

Before context compression or session exhaustion, the agent must tell the user:

- Why the session should end or move.
- What changed.
- Which files preserve the state.
- What the next session must read.
- What must not be repeated.
