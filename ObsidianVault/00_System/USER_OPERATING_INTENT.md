---
type: authority
title: User Operating Intent
status: active
created: 2026-07-03
---

# User Operating Intent

This file pins the top-level goal so that small tasks cannot quietly replace it. Charlie reads
this file as-is; it does not infer intent from conversation. Update it explicitly when the
user's priorities change.

## Top-level goal

Recover from drift since 2026-06-05 and stabilize the Obsidian Agent Brain System (Bucky OS) —
then move it to a 24/7 hosted environment (Oracle Cloud Always Free) while keeping GPU-dependent
work on the local PC.

## Core purpose

Efficient AI use, strong session memory across handoffs, efficient context management, and
evolution driven by user feedback rather than agent-invented scope.

## Critical failure mode

Bucky, Codex, and Claude Code becoming less useful together through shared degradation —
e.g. an unnoticed broken integration (git auto-push, dead Discord channel, missing dashboard
route) that nobody catches because no one audits the system as a whole.

## Knowledge loop

Daily Plus and GPT conversation exports feed the Obsidian knowledge library; the LLM Wiki,
Graphify, and Context Packs surface only the knowledge a task actually needs.

## Session continuity

When context grows large, leave behind: what changed, what to preserve, the read order for the
next session, and what not to repeat. Handoff documents in
`ObsidianVault/10_AgentBus/handoffs/` are the mechanism for this.

## Agent roles (source of truth)

- **Bucky** — work operations orchestrator.
- **Charlie** — independent system auditor (see `ObsidianVault/03_Projects/agents/charlie.md`).
- **Codex** — independent reviewer; implements only on explicit request.
- **Claude Code** — implementation within approved scope; commit/push only after explicit
  user approval (see `CLAUDE.md`).
