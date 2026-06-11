---
title: Sub-Agent Guidance
updated: 2026-05-30
status: canonical
owner: Bucky
tags:
  - #area/business_model
summary: "Sub-agents are role packets inside the Obsidian Agent Brain System. They are not independent authorities. Bucky routes work to them through Context Packs, AgentBus, or explicit instruction packets."
category: business_model
next_action: review
---

# Sub-Agent Guidance

Sub-agents are role packets inside the Obsidian Agent Brain System. They are not independent authorities. Bucky routes work to them through Context Packs, AgentBus, or explicit instruction packets.

## Current Sub-Agent Roles

| Role | Purpose | Reads | Writes |
|---|---|---|---|
| Context Dietitian | choose minimal context | request text, role map, Context Pack index | selected pack list or packet |
| ClaudeCode Builder | implement | implementation packet, target files, tests | code changes, verification notes |
| Codex Reviewer | verify independently | review packet, changed files, risks | user-facing review report |
| Knowledge Curator | compress knowledge | legacy/source notes, graph report | canonical notes, Context Pack updates |
| Archive Cleaner | classify stale material | legacy imports, conflict queues | archive decisions, cleanup manifests |
| Sync Sentinel | protect multi-PC state | sync protocol, git status, PC context | sync readiness and handoff notes |
| Dispatcher | move work across interfaces | AgentBus, Discord intake, queue state | routed task records |

## Dispatch Rule

Bucky dispatches only the smallest useful packet:

```powershell
python -X utf8 scripts/context_pack_selector.py --packet --project "<repo-or-folder>" "<request text>"
```

Sub-agents must not read the whole Vault, whole logs, or unrelated project instructions unless the packet explicitly expands scope.

## Shared Constraints

- Do not commit, push, delete, move, reset, or run non-dry-run migration without explicit user approval.
- Do not store secrets, API keys, passwords, webhook URLs, PII, or customer data in logs or AgentBus messages.
- Preserve user changes.
- Report evidence and blockers.
- Treat legacy paths as archive/reference-only unless a current Bucky packet says otherwise.

## Result Format

```yaml
agent: <role>
project: <repo-or-folder>
status: done | failed | blocked
changed_files:
  - <path>
verification:
  - <command or inspection result>
blockers:
  - <blocker or none>
next_action: <short next step>
```

## Relationship To Role Map

The authoritative role map is `ObsidianVault/03_Projects/agents/agent-house-role-map.md`. This file only describes how to apply those roles as task packets.
