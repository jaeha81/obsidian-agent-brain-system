---
type: context-pack
status: active
created: 2026-05-30
updated: 2026-05-30
owner: Bucky
scope: JH agent operating system
tags:
  - #area/ai_automation
  - #status/active
summary: "This pack absorbs useful operating rules from the old integrated JH setup into the current Obsidian Agent Brain System. Historical folders and generated global instruction files are reference-only; cu"
category: ai_automation
next_action: review
---

# Bucky Agent OS Legacy Rules Context Pack

This pack absorbs useful operating rules from the old integrated JH setup into the current Obsidian Agent Brain System. Historical folders and generated global instruction files are reference-only; current authority comes from Bucky, the project-local files, and this Vault.

## Top Rules

1. Obsidian Agent Brain System is the canonical JH agent operating system.
2. Bucky classifies user requests and provides scoped instruction packets to Claude Code and Codex.
3. Claude Code implements; Codex reviews independently unless the user explicitly asks Codex to operate.
4. Project instructions are project-scoped. Do not reuse another repo's instructions automatically.
5. New projects start with no project-specific packet until Bucky provides or confirms one.
6. Long legacy materials should be summarized into Context Packs instead of copied into prompts.
7. Commit, push, delete, move, reset, archive, and non-dry-run migration require explicit user approval.

## Request Handling

When a user request arrives, Bucky determines:

- project/repo/folder
- task type
- allowed scope
- forbidden operations
- required Context Packs
- verification evidence
- whether Claude Code, Codex, or both are needed

If Bucky is not actively waiting, agents use:

```text
python -X utf8 scripts/context_pack_selector.py "<request text>"
```

The selector is a trigger switch, not final authority. It identifies candidate packs so the active agent can stay inside the right context.

For a compact JSON packet that can be passed directly to Claude Code or Codex:

```text
python -X utf8 scripts/context_pack_selector.py --packet --project "<repo-or-folder>" "<request text>"
```

## Instruction Packet Shape

```yaml
project: current repo/folder
agent: ClaudeCode | Codex
role: implementation | review | verification | operation
scope: allowed files and task boundary
constraints: forbidden actions, approval gates, security rules
context_packs: selected packs
references: specific files to read
done_when: completion criteria and verification
fallback: minimum safe behavior if Bucky is unavailable
```

Packets should be compact. Use file paths for background material instead of pasting long text.

## Context Discipline

- Prefer `session-state.md`, current handoff, project-local `AGENTS.md`/`CLAUDE.md`, and selected Context Packs.
- Do not read huge logs or JSONL files in full.
- Search logs by date, target, status, or keyword.
- Do not read generated global Claude Code instructions as the first source.
- Do not apply old shared-folder rules as current operating rules.

## Replacement Map

| Old pattern | Current rule |
|---|---|
| shared folder as the main authority | ObsidianVault canonical sources |
| generated global Claude Code file first | Bucky packet and project-local instructions first |
| Agent Room as the single command window | Bucky as coordinator; AgentBus as record/queue |
| broad vault reread | targeted Context Pack and referenced file reads |
| direct migration writes | dry-run default plus explicit environment gate |

## Codex Rules

- Report review findings directly to the user.
- Read recurring error patterns before reviewing Claude output when applicable.
- Inspect recent/uncommitted changes by default for review tasks.
- Do not modify files unless the user explicitly asks.
- Never commit or push unless explicitly instructed.

## Claude Code Rules

- Implement inside the assigned scope.
- Preserve user changes and avoid unrelated refactors.
- Verify with the repo's established commands.
- Ask for a Bucky packet when a new project has no local instructions.
- Report blockers, changed files, and verification evidence.

## Approval Gates

Require explicit user approval for:

- commit or push
- destructive filesystem operations
- force reset or force push
- archive/move/delete operations
- non-dry-run legacy migration
- broad scans that are not needed for the direct task
- using credentials, API keys, or customer data

## Historical Source Access

Only read historical source material when a current Context Pack is insufficient and the request requires exact evidence. Narrow by file path, date, task id, or keyword first.

[[bucky-system-hub]]
