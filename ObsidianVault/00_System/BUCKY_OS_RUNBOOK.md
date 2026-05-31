---
type: runbook
status: active
owner: Bucky
updated: 2026-05-30
tags:
  - #status/active
---

# Bucky OS Runbook

This runbook is the short operating procedure for using Obsidian Agent Brain System as the JH agent instruction operating system.

## Startup Check

Run this before large agent work, migration work, global instruction changes, or new project packet rollout:

```powershell
python -X utf8 scripts/preflight_check.py
```

Expected Bucky line:

```text
bucky_os_gate: ok 19 checks
```

`preflight_check.py` may still warn about dirty Git state or network fetch failure. Those warnings do not invalidate Bucky OS gate unless `bucky_os_gate` itself reports `FAIL`.

## Direct Gate

Use the direct gate when the instruction authority state is the only thing being checked:

```powershell
python -X utf8 scripts/bucky_os_gate.py --fail-on-error
```

Required PASS checks:

- required files present;
- root `AGENTS.md` and `CLAUDE.md` point to Bucky;
- completion audit proves Codex, Claude Code, packet activation, and remaining boundary;
- default user-output policy is present in Bucky Context Packs;
- active-folder legacy Mneme/rank docs are marked superseded reference-only;
- legacy instruction inventory has no `candidate-review`, `high-priority-review`, or `secret-review-before-read`;
- current operating docs/scripts have no legacy authority review findings;
- secret manifest is tracked and value-free;
- secret decision register accounts for all secret-like candidates and stays value-free;
- legacy migration selector includes audit, inventory, residue, secret policy, and secret manifest;
- implementation/development selectors include the required Bucky packs;
- new project packet contract includes project boundary, no packet reuse, secret quarantine, Context Packs, and verification.

## Packet Selection

Use selector mode to see which Bucky-managed packs apply:

```powershell
python -X utf8 scripts/context_pack_selector.py "<request text>"
```

Use packet mode when Claude Code or Codex needs actionable JSON:

```powershell
python -X utf8 scripts/context_pack_selector.py --packet --project "<repo-or-folder>" "<request text>"
```

New projects start with no project-specific instructions unless a local packet exists. Do not reuse another repo/folder packet automatically.

## Legacy Migration Rule

For legacy instruction migration:

1. Run `scripts/bucky_os_gate.py --fail-on-error`.
2. Use `scripts/context_pack_selector.py "legacy instruction migration"` to confirm the Bucky migration packet.
3. Check `ObsidianVault/00_System/LEGACY_INSTRUCTION_INVENTORY_2026-05-30.md`.
4. Check `ObsidianVault/00_System/LEGACY_INSTRUCTION_CANDIDATE_AUDIT_2026-05-30.md`.
5. Do not open or promote secret-like archive material without following `ObsidianVault/00_System/LEGACY_SECRET_REVIEW_POLICY_2026-05-30.md`.
6. Re-run `scripts/legacy_residue_scanner.py` after each cleanup pass.

## Completion Boundary

A PASS gate proves current instruction authority and routing. It does not prove that every archived source file has been semantically rewritten. Archive material remains reference-only until Bucky promotes compressed, current-system rules into Context Packs or active framework docs.
