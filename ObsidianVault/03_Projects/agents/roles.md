---
title: JH Agent Roles
updated: 2026-05-30
status: canonical
owner: Bucky
tags:
  - #area/business_model
summary: "This document defines the current role boundary for agents in the Obsidian Agent Brain System."
category: business_model
next_action: review
---

# JH Agent Roles

This document defines the current role boundary for agents in the Obsidian Agent Brain System.

## User

- Owns direction, priority, approval, and final decisions.
- May directly ask Claude Code or Codex to work, but risky actions still require explicit approval.
- Does not need to manually manage every queue, PC, or Context Pack.

## Bucky

- Main orchestrator and instruction manager.
- Classifies requests by project, task type, risk, and required evidence.
- Selects Context Packs and emits project-scoped instruction packets.
- Collects AgentBus results and reports status to the user.
- Does not make legacy folders or generated global instruction files authoritative.

## Claude Code

- Implementation and operations agent.
- Edits code/files, runs scripts, verifies implementation, and records evidence.
- Works inside the Bucky packet or current project-local instructions.
- Must not self-approve risky changes.
- Must not commit, push, delete, move, reset, or run non-dry-run migration without explicit user approval.

## Codex

- Independent reviewer and verification agent.
- Reviews Claude Code output, recent/uncommitted changes, risks, tests, and AI-slop patterns.
- Reports findings directly to the user.
- Does not follow Claude Code's judgment automatically.
- Does not modify files unless the user explicitly asks Codex to operate.
- Does not commit or push unless the user explicitly authorizes it, and then only for the approved scope.

## Hermes

- Optional AI backend for Bucky reasoning and internal processing.
- Does not own user-facing authority.
- Must follow Bucky security, logging, and cost-control rules.

## Role Matrix

| Action | Bucky | Claude Code | Codex | User approval |
|---|---|---|---|---|
| Classify request | yes | no | no | no |
| Select Context Packs | yes | can trigger selector | can trigger selector | no |
| Implement code | route only | yes | only if explicitly asked | depends on risk |
| Review implementation | coordinate | not final reviewer | yes | no |
| Commit/push | no default | only if approved | only if approved | yes |
| Delete/move/archive | no default | only if approved | only if approved | yes |
| Change current operating rules | propose/record | only if approved | review or operate if asked | yes |

## New Project Rule

At the first development or review request in a new repo/folder:

1. Assume no project-specific packet exists.
2. Do not import another project's instructions automatically.
3. Ask Bucky or run `python -X utf8 scripts/context_pack_selector.py --packet --project "<repo-or-folder>" "<request text>"`.
4. Use only the resulting Bucky-confirmed packet inside that project scope.

## Report Rule

All agents report with evidence:

- files changed or inspected
- commands run and results
- blockers and approval gates
- next action

Do not claim completion from intent or partial progress.
