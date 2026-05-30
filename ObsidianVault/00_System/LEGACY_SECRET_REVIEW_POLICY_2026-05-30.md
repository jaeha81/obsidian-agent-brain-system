---
type: legacy-secret-review-policy
created: 2026-05-30
status: active
owner: Bucky
---

# Legacy Secret Review Policy

This policy governs archive/import sources that may contain API keys, tokens, passwords, webhooks, or private payloads.

## Source Of Truth

- Inventory: `ObsidianVault/00_System/LEGACY_INSTRUCTION_INVENTORY_2026-05-30.md`
- Value-free manifest: `ObsidianVault/00_System/LEGACY_SECRET_MANIFEST_2026-05-30.md`
- Value-free decision register: `ObsidianVault/00_System/LEGACY_SECRET_DECISION_REGISTER_2026-05-30.md`
- Security pack: `ObsidianVault/06_Context_Packs/bucky-security-runtime-governance.md`
- Candidate audit: `ObsidianVault/00_System/LEGACY_INSTRUCTION_CANDIDATE_AUDIT_2026-05-30.md`

## Status Rules

- `secret-review-before-read`: do not open broadly, quote, summarize, or copy into a Context Pack until a targeted redaction pass is complete.
- `secret-audit-mentioned`: already tracked by the audit, but still treat as sensitive if reopened.
- `audit-mentioned`: normal migration audit handling.
- `candidate-review`: normal promote / covered / archive-only decision.

## Review Steps

1. Use targeted path review only; do not scan or paste whole secret-like files into chat.
2. Redact literal keys, tokens, passwords, webhook URLs, and private payloads before any promotion.
3. Promote only compressed operational rules, never historical values or private examples.
4. If a value may have been real or externally exposed, report rotation as the required next action.
5. Preserve the source path and final decision in the candidate audit.

## Manifest Rules

- `scripts/legacy_secret_manifest.py` records path, pattern class, and line number only.
- The manifest must not include matched values or matched line text.
- `secret_review_before_read` must remain `0` before Bucky packets can use any legacy migration source as context.
- `scripts/bucky_os_gate.py` must fail if the manifest contains literal key-shaped values, webhook URLs, or matched-text/excerpt columns.

## Decision Register Rules

- `scripts/legacy_secret_decision_register.py` records a value-free handling decision for every manifest entry.
- The register must account for all secret-like candidates in the manifest.
- The register must not include matched values, webhook URLs, matched line text, or excerpts.
- `archive-only`, `covered-quarantined`, and `partial-promoted-quarantined` are safe operating decisions because they do not require reopening the secret-like source broadly.
- `pending-targeted-redaction` means the source cannot be used for additional promotion until a targeted redaction pass reviews only the manifest-listed lines.
