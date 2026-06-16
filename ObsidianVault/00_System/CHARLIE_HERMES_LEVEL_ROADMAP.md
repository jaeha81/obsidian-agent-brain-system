---
type: charlie-hermes-level-roadmap
status: active
created: 2026-06-16
owner: Charlie
---

# Charlie Hermes-Level Roadmap

Charlie must grow beyond a passive checklist. It should provide Hermes-level operational visibility for the Obsidian Brain System while staying inside Charlie's audit role.

## Mission

Charlie protects efficient AI use, stronger memory, context efficiency, user-feedback evolution, Daily Plus/GPT capture, and selective retrieval through Obsidian, LLM Wiki, Graphify, and Context Packs.

Charlie does not replace Bucky. Charlie audits the system, reports drift, and asks the user for approval before corrective action.

## Hermes-Level Capabilities

| Hermes/Bucky Benchmark | Charlie Equivalent | Minimum Evidence |
|---|---|---|
| Pantheon graph | Role-boundary graph for Bucky, Codex, Claude Code, Charlie, Discord, Daily Plus, dashboards, and Context Packs | Source files and current status for each node |
| Memory stack | Intent, session continuity, error registry, handoff, and context-pack health layers | `USER_OPERATING_INTENT.md`, handoff files, registries |
| AI spend | Context waste, repeated instructions, ping-pong loops, and avoidable agent dispatch tracking | Error registry entries and turn-closure checks |
| Mission control | Charlie recovery goals and open warnings | `charlie_audit.py --no-write` status and dirty worktree classification |
| Dreaming function | Daily drift insight and repeat-pattern report | Charlie error registry plus daily/weekly summary |
| Obsidian graph | Knowledge-loop health for Daily Plus, GPT capture, LLM Wiki, Graphify, and Context Packs | Targeted retrieval proof instead of broad vault reads |
| Agent health | Runtime and channel status for Bucky, Discord, dashboards, and home PC | Live process/channel/preview evidence |

## Discord Channel

`#jh-charlie` is Charlie's user-facing system-audit channel.

Purpose:

- Report Charlie audit state.
- Ask for user confirmation on restore, cleanup, permission, or authority changes.
- Track home PC continuity issues.
- Surface repeated mistakes and next work directives.

Non-goals:

- It is not a normal Bucky work queue.
- It must not auto-assign Claude Code work.
- It must not spam continuous status updates.

Runtime key:

- `JH_CHARLIE_CHANNEL_ID`

## Phase Plan

### Phase 1: Channel And Guardrails

- Add `JH_CHARLIE_CHANNEL_ID`.
- Auto-create or discover `#jh-charlie`.
- Load Charlie-specific context in that channel.
- Keep `charlie_audit.py --no-write` as the primary deterministic check.

### Phase 2: Status Model

- Define Charlie status JSON fields without forcing writes where permissions fail.
- Track active request queue, open warnings, dirty worktree summary, and next work directive.
- Add dashboard bootstrap fallback when JSON is missing.

### Phase 3: Evidence Dashboard

- Show Charlie warning count, worktree risk, authority files, specialist roster, and knowledge-loop health.
- Link evidence files instead of pasting long logs.

### Phase 4: Daily Drift Insight

- Summarize repeated errors, stale authority signals, runtime proof gaps, and unresolved user corrections.
- Send a compact report to `#jh-charlie` only when there is a meaningful change.

## Success Criteria

- Charlie reports never omit open work and next directive.
- Charlie channel exists and is allowed.
- Charlie audit stays deterministic and low-token.
- Daily Plus/GPT to Obsidian knowledge loop is explicitly protected.
- The user can see what Charlie knows, what is still open, and what needs approval.
