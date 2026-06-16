# Charlie System Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Charlie as an independent, low-token system audit layer for the Obsidian Brain System.

**Architecture:** Charlie is not a work orchestrator. It records user intent, audits instructions and runtime drift with deterministic checks, writes JSON evidence, and exposes an independent static dashboard.

**Tech Stack:** Markdown operating docs, Python standard library audit script, static HTML dashboard.

---

### Task 1: Authority Documents

**Files:**
- Create: `ObsidianVault/03_Projects/agents/charlie.md`
- Create: `ObsidianVault/00_System/USER_OPERATING_INTENT.md`

- [ ] Define Charlie as the independent system audit agent.
- [ ] Define Bucky as the work operations orchestrator, not the system auditor.
- [ ] Pin the user's top-level operating intent so small tasks cannot replace it.

### Task 2: Registries

**Files:**
- Create: `ObsidianVault/00_System/CHARLIE_ERROR_REGISTRY.md`
- Create: `ObsidianVault/00_System/CHARLIE_CHANGE_LOG.md`
- Create: `ObsidianVault/00_System/PROJECT_INSTRUCTION_REGISTRY.md`

- [ ] Add a repeat-error registry format.
- [ ] Add a change log format centered on risk and user approval.
- [ ] Add a project instruction registry for `AGENTS.md`, `CLAUDE.md`, and `OPERATING_INTENT.md`.

### Task 3: Low-Token Audit Script

**Files:**
- Create: `scripts/charlie_audit.py`

- [ ] Use only deterministic local checks.
- [ ] Detect missing instruction packets.
- [ ] Detect stale dates, stale PIDs, and gate-state mismatches.
- [ ] Summarize `git log --since=2026-06-05` by risk area.
- [ ] Write `data/charlie/charlie_status.json` and `docs/data/charlie_status.json`.
- [ ] Never modify code, instructions, runtime state, or git.

### Task 4: Independent Dashboard

**Files:**
- Create: `docs/charlie-system-audit.html`

- [ ] Fetch `data/charlie_status.json`.
- [ ] Show System Integrity, Agent Oversight, Change Timeline, Error Registry, Instruction Registry, and User Intent.
- [ ] Make clear that Charlie reports and blocks drift, but does not auto-fix.

### Task 5: Verification

**Commands:**
- `python -m py_compile scripts\charlie_audit.py`
- `python scripts\charlie_audit.py --json`
- `Test-Path docs\data\charlie_status.json`
- `git diff --stat`

- [ ] Confirm generated JSON exists.
- [ ] Confirm dashboard is independent.
- [ ] Confirm no commit or push was made.
