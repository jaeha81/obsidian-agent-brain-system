---
type: context-pack
status: active
owner: Bucky
created: 2026-05-30
source:
  - ObsidianVault/09_Archive/legacy-import/legacy-import/OBSIDIAN-SECOND/claude-knowledge/preferences/context-usage-principle.md
  - ObsidianVault/09_Archive/legacy-import/legacy-import/OBSIDIAN-SECOND/claude-knowledge/errors/context-waste-patterns.md
  - ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/Codex_Goal_Mode_Playbook.md
tags:
  - #area/ai_automation
  - #status/active
---

# Bucky Context Efficiency and Goal Mode Pack

## Purpose

This pack promotes legacy integration-system operating rules into the current Obsidian Agent Brain System. Bucky must use these rules when dispatching work to Claude Code/Codex or when answering directly.

## Context Efficiency Rules

1. Use the smallest current source that can answer the request.
2. When the user gives a complete summary, treat that summary as working context and read underlying files only when verification is needed.
3. Prefer narrow pointers in this order: current user summary, `session-state.md`, exact daily report, exact handoff, then targeted `rg`.
4. Do not read whole large logs by default. Narrow by date, speaker, target, status, or keyword first.
5. Do not inspect global instructions or large logs only to detect PC environment. Use low-cost checks such as `Test-Path`, current path, git status, and `whoami`.
6. If a project appears empty or the source path is unclear, infer from the current request when safe; otherwise ask for the missing source instead of broad exploration.
7. Treat Google Drive sync folders as shared state/doc storage, not as authoritative git repositories unless a real `.git` root is verified.
8. Avoid re-reading files already summarized in the active session unless a current-state check is necessary.

## Goal Mode Rules

Goal work is not a one-shot prompt. It is a loop:

```text
goal definition -> execution -> verification -> record -> revise or finish
```

Bucky should turn broad user objectives into a measurable checklist before dispatching long work.

Minimum goal packet:

```yaml
goal: concrete outcome
baseline: current known state
target_state: measurable desired state
verification: commands, files, runtime checks, or checklist evidence
done_when: explicit completion conditions
constraints: forbidden actions, approval gates, scope limits
record_path: where result/evidence is saved in ObsidianVault
next_action: immediate first step
```

Completion cannot be claimed from intent, partial progress, or lack of obvious errors. Bucky/Claude/Codex must inspect evidence that matches the scope of the goal.

## Dispatch Rules

- Claude Code receives implementation/operator packets.
- Codex receives independent review/debug/verification packets.
- For ambiguous or high-risk work, Bucky must include `scope`, `constraints`, `done_when`, and `verification` in the packet.
- For new repos/folders, Bucky must issue a project-specific packet and must not reuse another project's instructions automatically.

## Anti-Waste Alerts

Flag these patterns as operational errors:

- broad vault scan before checking the current handoff or session state;
- full JSONL/log read before a targeted search;
- repeated reading of already summarized material;
- direct execution of legacy scripts before classification;
- premature closeout before verification evidence is saved;
- expanding a screen/runtime error into unrelated architecture cleanup.
