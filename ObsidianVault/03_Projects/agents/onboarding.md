---
title: JH Agent Onboarding
migrated_from: G:\내 드라이브\JH-SHARED\00_SYSTEM\agent-onboarding.md
migrated_date: 2026-05-24
updated: 2026-05-30
status: canonical
tags:
  - #area/business_model
summary: "Read this when an agent starts work in the JH ecosystem or when a user asks to resume, sync, review, or begin a new project."
category: business_model
next_action: review
---

# JH Agent Onboarding

Read this when an agent starts work in the JH ecosystem or when a user asks to resume, sync, review, or begin a new project.

## First Principles

- Obsidian Agent Brain System is the main agent operating system.
- Bucky is the instruction manager and activation switch.
- Claude Code implements.
- Codex reviews independently.
- Legacy JH-SHARED and OBSIDIAN-SECOND files are archive/reference-only unless a current Bucky packet says otherwise.

## Minimal Startup Reads

1. `ObsidianVault/00_System/BUCKY_CONTEXT.md`
2. `ObsidianVault/00_System/ROUTING_RULES.md`
3. `ObsidianVault/05_Frameworks/guides/sync-protocol.md`
4. `ObsidianVault/05_Frameworks/guides/paths.md`
5. `ObsidianVault/06_Context_Packs/index.md`

For a specific request, run `python -X utf8 scripts/context_pack_selector.py "<request text>"` to select the smallest Bucky-managed pack set.

For a directly usable instruction packet, run:

```powershell
python -X utf8 scripts/context_pack_selector.py --packet --project "<repo-or-folder>" "<request text>"
```

## New Project Rule

At the first development request in a new repo/folder, assume there is no project-specific packet yet. Do not import instructions from another repo automatically. Ask Bucky for a project packet or use the Bucky selector to identify the relevant current Context Packs.

## Do Not

- Do not read global `~/.claude/CLAUDE.md` as the first source of truth.
- Do not use `JH-SHARED` as the active shared workspace.
- Do not scan whole archives or huge logs without a targeted reason.
- Do not commit, push, delete, move, or run legacy migration writes without explicit approval.

## Confirmation Phrase

```text
JH agent onboarding confirmed: Bucky-centered Agent OS, role boundaries, current Vault paths, and minimal context rules are loaded.
```
