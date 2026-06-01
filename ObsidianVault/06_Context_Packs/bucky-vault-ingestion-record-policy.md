---
type: context-pack
status: active
owner: Bucky
created: 2026-05-30
source:
  - ObsidianVault/09_Archive/legacy-import/legacy-import/OBSIDIAN-SECOND/CLAUDE.md
  - ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/03_Prompts/templates/session-summary.md
  - ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/03_Prompts/templates/decision-log.md
  - ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/03_Prompts/templates/jh-daily-retrospective.md
  - ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/03_Prompts/templates/jh-metadata-template.md
  - ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/03_Prompts/templates/agent-skill.md
  - ObsidianVault/09_Archive/migration-conflicts/2026-05-24/*/raw/memories2/11_Obsidian_세컨드브레인_체크포인트.md
tags:
  - #area/ai_automation
  - #status/active
summary: "type: session-summary"
category: ai_automation
next_action: review
---

# Bucky Vault Ingestion and Record Policy

## Purpose

This pack converts legacy LLM Wiki and template rules into the current Obsidian Agent Brain System. Bucky uses it when importing knowledge, creating durable notes, saving decisions, or asking Claude Code/Codex to produce session evidence.

## Operating Model

- The current ObsidianVault is the source of truth for agent operating memory.
- Legacy `wiki/`, `raw/`, and `templates/` paths are sources only. They must not become active operating roots again.
- Preserve source traceability in every promoted note or context pack.
- Original imported source material should be treated as immutable evidence. Promote summaries and rules, not broad copied source folders.

## Ingest Workflow

When useful external or legacy source material is accepted:

1. Identify source type: article, note, session, handoff, decision, template, project memory, or raw data.
2. Preserve the source path or URL in frontmatter or a `Source` section.
3. Extract only reusable claims, rules, decisions, patterns, and next actions.
4. Create or update the correct current-system destination:
   - operating rules -> `ObsidianVault/06_Context_Packs/`
   - agent routing/system policy -> `ObsidianVault/00_System/`
   - reusable framework guidance -> `ObsidianVault/05_Frameworks/`
   - project-specific memory -> `ObsidianVault/03_Projects/`
   - knowledge notes -> `ObsidianVault/03_Knowledge/`
   - AgentBus handoff/evidence -> `ObsidianVault/10_AgentBus/`
5. Add links to relevant index, audit, or status files.
6. Record what was promoted, what was left as archive-only, and why.

## Query Workflow

When answering from Vault knowledge:

1. Start from the current index, hub, handoff, or context pack.
2. Read at most the directly relevant notes first.
3. Synthesize an answer with source paths and uncertainty.
4. If a useful answer should become durable knowledge, propose or create a note in the current Vault structure.

## Checkpoint Workflow

For second-brain or long-running agent work, Bucky should maintain checkpoints in current Vault paths rather than legacy roots.

Checkpoint records should preserve:

- objective and current status;
- decisions made and why;
- changed files or knowledge assets;
- verification evidence;
- unresolved blockers;
- exact next-start files or commands;
- whether the checkpoint is project-specific or global.

Do not store secret values, private payloads, full logs, or customer data in checkpoint notes. Store paths and redacted summaries instead.

## Lint Workflow

Bucky should flag these knowledge-base health issues:

- contradictory rules across current packs;
- current docs pointing to legacy roots as if they are active;
- orphaned promoted notes with no index/status/audit reference;
- source claims without source path/date;
- stale pricing/API/provider facts presented as current;
- templates that omit owner, status, date, source, next action, or verification.

## Required Record Shapes

### Session Summary

```yaml
type: session-summary
date:
agent:
project:
completed:
decisions:
next_session:
blockers:
evidence_paths:
```

### Decision Log

```yaml
type: decision
date:
topic:
status:
context:
decision:
rationale:
impact_scope:
follow_up:
links:
```

### Daily Retrospective

```yaml
type: daily-retrospective
date:
development_assets:
knowledge_assets:
solved_problems:
next_actions:
system_status:
```

### Agent Skill / Operating Procedure

```yaml
type: skill
agent:
version:
purpose:
inputs:
outputs:
steps:
constraints:
examples:
related_notes:
```

## Dispatch Rule

When Bucky asks Claude Code/Codex to create durable evidence, it should name the exact record shape and destination path instead of asking for an unstructured summary.
