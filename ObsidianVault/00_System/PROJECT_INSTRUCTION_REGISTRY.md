---
type: project-instruction-registry
status: active
created: 2026-06-15
---

# Project Instruction Registry

This registry tracks whether each project can operate without relying on live Bucky context.

## Required Packet

| File | Purpose |
|---|---|
| `AGENTS.md` | Codex role, boundaries, review/implementation rules |
| `CLAUDE.md` | Claude Code role, implementation rules, verification expectations |
| `OPERATING_INTENT.md` | User-specific long-term purpose for the project |

## Current Project

| Project | Path | AGENTS.md | CLAUDE.md | OPERATING_INTENT.md | Status |
|---|---|---:|---:|---:|---|
| Obsidian Agent Brain System | `G:\내 드라이브\obsidian-agent-brain-system` | present | present | needs local project file | watch |
| shorts-dashboard | `D:\ai프로젝트\쇼츠자동화\shorts-dashboard` | present | present | n/a (code project) | active |

## Rule

When a project lacks a local instruction packet, agents must not import another repository's instructions automatically. They should request or generate a packet for user approval.

## Context Packs

| Project | Context Pack |
|---|---|
| Obsidian Agent Brain System | `ObsidianVault/06_Context_Packs/bucky-*.md` (all) |
| shorts-dashboard | `ObsidianVault/06_Context_Packs/bucky-shorts-dashboard.md` |
