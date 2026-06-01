---
type: context-pack
status: active
owner: Bucky
created: 2026-05-30
freshness: legacy-derived; applies as user preference unless contradicted by a current project packet
source:
  - ObsidianVault/00_System/LEGACY_INSTRUCTION_INVENTORY_2026-05-30.md
  - ObsidianVault/03_Projects/agents/mneme.md
  - ObsidianVault/03_Projects/agents/agent-dispatcher.md
tags:
  - #area/ai_automation
  - #status/active
summary: "This pack promotes user-facing communication preferences from legacy material into the current Obsidian Agent Brain System. It is a default pack for Bucky, Claude Code, and Codex because it affects ev"
category: ai_automation
next_action: review
---

# Bucky User Communication and Output Policy

## Purpose

This pack promotes user-facing communication preferences from legacy material into the current Obsidian Agent Brain System. It is a default pack for Bucky, Claude Code, and Codex because it affects every instruction packet, status report, handoff, and final answer.

## Core Rules

1. Prefer Korean for user-facing explanations when the user writes Korean. Keep file paths, commands, code identifiers, and API names in English.
2. Be direct: facts, risks, next actions, and verification evidence first.
3. Avoid unnecessary flattery, repeated context, or long explanations of things the user already knows.
4. When giving a prompt, command sequence, or developer instruction for the user to execute, provide a single copyable block when possible.
5. Do not mix the actual prompt/command with surrounding prose in a way that makes the executable part ambiguous.
6. If explanation is needed, put it before or after the copyable block and keep it short.
7. For long work, report durable evidence: changed files, reports, exact commands run, verification result, remaining blockers, and next-start files.
8. Do not declare completion from intention or partial progress. Completion requires current evidence.
9. When the user gives a concrete before/after list, remaining-work list, or validation spec, treat it as the working acceptance criteria.
10. If output must be reused by another agent, prefer compact structured fields over long prose: `goal`, `scope`, `constraints`, `references`, `verification`, `done_when`, `next_action`.

## Copyable Output Standard

Use a fenced block for any final prompt, shell command set, JSON packet, YAML packet, or instruction payload that the user may copy elsewhere.

```text
<single copyable payload>
```

Do not put hidden prerequisites only in prose if the block depends on them.

## Status Report Standard

For Bucky-mediated work, the short status report should include:

- current state;
- what changed;
- proof command or file;
- what remains;
- whether user approval is needed.

## Agent Dispatch Standard

When Bucky sends work to Claude Code or Codex, the packet should be short enough to fit in the agent prompt without waste. Long background belongs in referenced Context Packs or exact Vault paths.

Minimum packet:

```yaml
project: <repo-or-folder>
agent: <ClaudeCode|Codex>
goal: <concrete outcome>
scope: <allowed files and boundaries>
constraints: <approval and safety rules>
references:
  - <path>
verification:
  - <command or inspection>
done_when: <measurable completion>
next_action: <first step>
```

## Source Handling Note

One source signal came from a secret-like legacy inventory excerpt, not from reopening the quarantined source file. Do not reopen or quote that source unless a targeted redaction pass is approved and documented under `LEGACY_SECRET_REVIEW_POLICY_2026-05-30.md`.
