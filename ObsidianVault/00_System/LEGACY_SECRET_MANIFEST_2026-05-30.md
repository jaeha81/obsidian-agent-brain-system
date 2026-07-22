---
type: legacy-secret-manifest
created: 2026-05-30T07:32:12
status: active
owner: Bucky
tags:
  - #status/active
---

# Legacy Secret Manifest

This report intentionally omits secret values and line text. It records only paths, pattern classes, and line numbers.

- Secret-like candidates: 31
- secret-audit-mentioned: 31
- pattern:api_key_word: 5
- pattern:secret_word: 1
- pattern:token_word: 12
- pattern:webhook_word: 14

## Handling

1. Do not paste matched line text into chat or Context Packs.
2. Open a listed file only for targeted redaction or rotation assessment.
3. Promote compressed rules only after literal values/private examples are removed.
4. Keep the archive path and final decision in the candidate audit.

## Entries

| Status | Path | Pattern classes | Lines | Action |
|---|---|---|---|---|
| secret-audit-mentioned | `ObsidianVault/09_Archive/legacy-import/legacy-import/OBSIDIAN-SECOND/raw/gpt/메모리.txt` | webhook_word | 93, 185, 193, 205, 211, 219, 233 | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/legacy-import/legacy-import/Obsidian-Vault/01_Projects/knowledge/gpt-memory/gpt-memory-projects.md` | webhook_word | 25, 47 | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/legacy-import/legacy-import/Obsidian-Vault/01_Projects/knowledge/gpt-memory/gpt-memory-tech-stack.md` | webhook_word | 21, 42, 53 | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/legacy-import/legacy-import/Obsidian-Vault/raw/memories2/06_기술스택_개발원칙 (1).md` | webhook_word | 44, 154 | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/_organized/merge-candidate/OBSIDIAN-SECOND/raw/memories2/11_Obsidian_세컨드브레인_체크포인트.md` | webhook_word | 65 | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/_organized/preserve-legacy/JH-Agent-Room/README.md` | secret-hint | unknown | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/_organized/superseded/Obsidian-Vault/03_Prompts/ai-api/ai-api-routing-architect.md` | api_key_word, token_word, webhook_word | 188, 189, 269, 295, 296, 297, 298, 299, 300, 301, 302, 303, 306 | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/_organized/superseded/Obsidian-Vault/output/codex-review-targets/2026-05-12-infranodus-functional-verification.md` | api_key_word | 61 | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/_organized/superseded/Obsidian-Vault/raw/memories/05_jh_estimate_ai.md` | token_word | 77 | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/_organized/superseded/Obsidian-Vault/raw/memories/06_jh_harness.md` | token_word | 35 | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/_organized/superseded/Obsidian-Vault/raw/memories/12_ai_tools.md` | token_word | 61, 105 | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/_organized/superseded/Obsidian-Vault/raw/memories2/11_Obsidian_세컨드브레인_체크포인트.md` | webhook_word | 65 | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/_organized/superseded/Obsidian-Vault/raw/memories2/12_보안_법적기준.md` | webhook_word | 110 | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/_organized/superseded/Obsidian-Vault/raw/memories2/13_개발_프롬프트_템플릿.md` | webhook_word | 196 | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/_organized/superseded/Obsidian-Vault/wiki/jh-infranodus-upgrade-analysis.md` | secret-hint | unknown | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/JH-Agent-Room/README.md` | secret-hint | unknown | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/OBSIDIAN-SECOND/raw/memories2/11_Obsidian_세컨드브레인_체크포인트.md` | webhook_word | 65 | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/03_Prompts/ai-api/ai-api-routing-architect.md` | api_key_word, token_word, webhook_word | 188, 189, 269, 295, 296, 297, 298, 299, 300, 301, 302, 303, 306 | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/output/codex-review-targets/2026-05-12-infranodus-functional-verification.md` | api_key_word | 61 | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/raw/memories/05_jh_estimate_ai.md` | token_word | 77 | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/raw/memories/06_jh_harness.md` | token_word | 35 | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/raw/memories/12_ai_tools.md` | token_word | 61, 105 | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/raw/memories2/11_Obsidian_세컨드브레인_체크포인트.md` | webhook_word | 65 | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/raw/memories2/12_보안_법적기준.md` | webhook_word | 110 | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/raw/memories2/13_개발_프롬프트_템플릿.md` | webhook_word | 196 | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/wiki/jh-infranodus-upgrade-analysis.md` | secret-hint | unknown | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/sessions/2026-05-15-07-51-08.md` | api_key_word, secret_word | 16 | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/sessions/2026-05-16-23-40-44-544-codex-20260516-234040-codex.md` | token_word | 24 | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/sessions/2026-05-17-06-40-51-844-codex-20260517-064047-codex.md` | token_word | 25 | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/sessions/2026-05-17-07-18-31-857-codex-20260517-071827-codex.md` | token_word | 26, 50 | quarantined; targeted redaction review required before promotion |
| secret-audit-mentioned | `ObsidianVault/09_Archive/sessions/2026-05-20-09-03-03-126-codex-20260520-session-end-codex.md` | token_word | 9 | quarantined; targeted redaction review required before promotion |

[[bucky-system-hub]]
