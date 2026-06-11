---
type: agent-role-map
status: canonical
created: 2026-05-27
graph_role: instruction-node
master_plan: ObsidianVault/00_UPGRADE/obsidian-brain-stabilization-and-agent-house-master-plan-2026-05-27.md
tags:
  - #area/business_model
summary: "The Obsidian Agent Brain System is the house. Agents are workers inside the house."
category: business_model
next_action: review
---

# Agent House Role Map

## Operating Rule

The Obsidian Agent Brain System is the house. Agents are workers inside the house.

No single agent owns the whole system. Each agent receives only the context needed for its role, performs the task, and writes back a traceable result.

## Roles

| Role | Purpose | Reads | Writes | Must Not Do |
|---|---|---|---|---|
| User / Owner | Direction, priority, final approval | Status summaries, review reports, next-action prompts | Decisions and approvals | Manually track every PC or queue detail |
| Bucky Operator | Front desk, queue, routing, Discord status | `session-resume.md`, AgentBus queues, Discord messages, role map | Status notes, queue updates, user-facing summaries | Act as final reviewer of its own implementation path |
| Codex Reviewer | Independent review and risk detection | Review context pack, changed files, risk patterns, task acceptance criteria | Direct user review report, review result files | Implement code unless user explicitly switches role |
| ClaudeCode Builder | Implementation and migration worker | Implementation context pack, target files, tests, acceptance criteria | Code changes, migration outputs, implementation reports | Self-approve without Codex review on risky work |
| Knowledge Curator | Canonical note and graph organization | Imported notes, graph report, wiki/project/framework notes | Canonical nodes, merge notes, graph cleanup queues | Bulk absorb legacy content without classification |
| Archive Cleaner | Separate stale, duplicate, and legacy material | Legacy imports, conflict queues, archive candidates | Archive decisions, deprecation notes, cleanup manifests | Delete or move original legacy sources without explicit approval |
| Context Dietitian | Keep agents light | Task type, role map, context pack index, session entry | Selected context pack list | Force every agent to read all instructions |
| Sync Sentinel | Multi-PC and storage safety | PC detection guide, Git status, Google Drive path, GitHub remote, Docker state | PC status, storage warnings, sync readiness notes | Let secondary PCs become silent authorities |
| Dispatcher / Driver | Move work between interfaces and agents | Discord intake, AgentBus protocol, queue state | Routed task records, fallback notices | Lose work when Discord, a bot, or a local process fails |

## Handoff Rules

1. User intent enters through Discord, Obsidian, local terminal, or GitHub.
2. Bucky identifies task type and asks the Context Dietitian for the smallest useful context pack.
3. Dispatcher sends the task to ClaudeCode, Codex, curator, cleaner, or sync sentinel.
4. Worker writes result to the correct persistent layer: AgentBus, Obsidian note, GitHub, or daily report entry.
5. Codex reviews implementation or risky routing changes independently.
6. Bucky reports status to the user and links the persistent record.

## Graph Node Tags

Use these graph roles in frontmatter when creating new operating notes:

- `canonical-node`: current truth.
- `instruction-node`: role or agent instruction.
- `skill-node`: reusable procedure.
- `project-node`: active project or workstream.
- `handoff-node`: session, PC, or agent continuation.
- `legacy-node`: source material awaiting absorption decision.
- `archive-node`: preserved history, not active instruction.
- `risk-node`: known unsafe path, stale rule, or failure pattern.

## First Implementation Boundary

This map defines roles. It does not yet create separate runtime processes for every role.

Initial implementation can be prompts, context packs, dispatcher rules, or review checklists. Runtime automation should be added only after the role boundary is clear and testable.
