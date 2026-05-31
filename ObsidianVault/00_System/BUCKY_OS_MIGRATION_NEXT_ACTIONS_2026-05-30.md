---
type: migration-next-actions
status: active
owner: Bucky
created: 2026-05-30
tags:
  - #status/active
---

# Bucky OS Migration Next Actions

Purpose: keep the full objective alive after the current pass. Obsidian Agent Brain System is now the active instruction operating system, but legacy data absorption is not fully exhausted.

## Current Proven State

- Bucky OS gate: PASS, 19 checks.
- Preflight exposes `bucky_os_gate: ok 19 checks`.
- Legacy instruction inventory: 347 candidates tracked.
- Candidate review backlog: 0.
- Secret-like tracked/quarantined candidates: 31.
- Secret decision register: 9 archive-only, 20 covered-quarantined, 2 partial-promoted-quarantined, 0 pending-targeted-redaction.
- Active residue scan: 0 review findings, 657 allowed archive/superseded mentions.
- Default packets now include `bucky-user-communication-output-policy.md`.
- Active-folder legacy Mneme/rank documents are marked superseded reference-only.

## Newly Promoted In This Pass

| Source | Destination | Handling |
|---|---|---|
| `LEGACY_INSTRUCTION_INVENTORY_2026-05-30.md` safe excerpt from `OBSIDIAN-SECOND/raw/gpt/메모리.txt` | `ObsidianVault/06_Context_Packs/bucky-user-communication-output-policy.md` | promoted copyable-output and low-ambiguity prompt rules without reopening quarantined source |
| `ObsidianVault/03_Projects/agents/mneme.md`, `agent-dispatcher.md` | `bucky-user-communication-output-policy.md` | promoted concise Korean/direct-report user communication rules |
| `COMMON-PHILOSOPHY.md`, `mneme.md`, `rank-system.md`, `evolution.md` | file-top superseded warnings | blocked old active-folder authority from overriding Bucky |

## Next High-Value Work

1. Re-check quarantined sources only if a future task needs source-specific detail.
2. If future targeted redaction finds new reusable non-secret rules, extract only compressed rules into existing Context Packs or a new pack.
3. Keep all secret-like legacy files quarantined unless redaction evidence proves safe extraction.
3. Re-run:

```powershell
python -X utf8 scripts/legacy_secret_manifest.py --report ObsidianVault/00_System/LEGACY_SECRET_MANIFEST_2026-05-30.md
python -X utf8 scripts/legacy_secret_decision_register.py --report ObsidianVault/00_System/LEGACY_SECRET_DECISION_REGISTER_2026-05-30.md
python -X utf8 scripts/legacy_residue_scanner.py --report ObsidianVault/00_System/LEGACY_RESIDUE_SCAN_2026-05-30.md
python -X utf8 scripts/bucky_os_gate.py --fail-on-error
python -X utf8 scripts/preflight_check.py
```

## Do Not Do

- Do not make legacy folders authoritative again.
- Do not quote or copy secret-like source lines into packets.
- Do not treat old Mneme, rank, or Agent Room docs as current authority.
- Do not claim raw archive data redaction complete; secret-like legacy files remain quarantined even when their operating-rule decisions are accounted for.
