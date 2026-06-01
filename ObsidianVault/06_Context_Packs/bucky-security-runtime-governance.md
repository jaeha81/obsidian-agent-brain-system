---
type: context-pack
status: active
owner: Bucky
created: 2026-05-30
source:
  - ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/raw/memories/03_tech_stack.md
  - ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/raw/memories/06_jh_harness.md
  - ObsidianVault/09_Archive/migration-conflicts/2026-05-24/Obsidian-Vault/raw/memories/12_ai_tools.md
  - ObsidianVault/09_Archive/legacy-import/legacy-import/Obsidian-Vault/raw/memories2/06_기술스택_개발원칙 (1).md
  - ObsidianVault/09_Archive/migration-conflicts/2026-05-24/_organized/superseded/Obsidian-Vault/raw/memories2/12_보안_법적기준.md
tags:
  - #area/ai_automation
  - #status/active
summary: "This pack promotes legacy runtime safety, security, and agent-control rules into the current Obsidian Agent Brain System."
category: ai_automation
next_action: review
---

# Bucky Security and Runtime Governance

## Purpose

This pack promotes legacy runtime safety, security, and agent-control rules into the current Obsidian Agent Brain System.

## Control Principles

1. The user controls direction and approval. AI agents execute only inside explicit scope.
2. Supervisor/orchestrator and executor roles must remain separate.
3. YAML or markdown declarations alone do not enforce behavior. Critical controls must be implemented in code, runtime checks, permissions, or review gates.
4. Project-specific `AGENTS.md`/`CLAUDE.md` rules override generic preferences inside that project, but cannot weaken security or approval requirements.
5. High-risk operations require explicit approval: deletion, push, deployment, payments, credential changes, public data release, and customer-data processing.

## Security Rules

- Never paste `.env`, API keys, passwords, webhook URLs, DB credentials, PII, or customer secrets into chat, logs, source files, or screenshots.
- If secret-like data is detected, stop, report, redact, and recommend rotation when exposure is plausible.
- Legacy archive paths marked `secret-review-before-read` in `ObsidianVault/00_System/LEGACY_INSTRUCTION_INVENTORY_2026-05-30.md` must not be opened broadly or promoted into packets until manually redacted.
- Legacy archive paths marked `secret-audit-mentioned` are tracked but still require the same redaction discipline if reopened.
- API keys must live in environment variables or managed secret stores, not frontend code.
- Uploaded files, images, audio, documents, and customer data require retention and access-scope decisions.
- Logs must not store API keys, PII, customer secrets, full sensitive payloads, or private business strategy.
- Public GitHub repositories must not receive local logs, `.env`, private vault data, customer records, or generated secret dumps.

## Runtime Logging Rules

- File logs are useful evidence but are not enforcement. They can be deleted or edited.
- For production or safety-critical agent actions, prefer append-only or DB-backed audit logs.
- Log at least: actor, action, target, timestamp, status, error, approval reference, and evidence path.
- Separate operational logs from customer data and test data from production data.

## Agent Execution Rules

- Do not let an agent both decide and execute high-risk actions without a review/approval step.
- Use a single human intervention point for sensitive operations.
- When multiple agents run in parallel, assign task IDs, locks, and output paths.
- Bucky should dispatch by role:
  - planner/supervisor: classify and decide;
  - implementer/executor: modify or run;
  - reviewer: verify independently;
  - archivist/recorder: preserve evidence.

## Code Quality Defaults

These are defaults, not universal project law. Apply them when they do not conflict with the local repo:

- prefer clear named exports in TypeScript modules;
- avoid `any` and unnecessary `unknown`;
- keep each file's responsibility clear;
- avoid duplicate API endpoint designs;
- use async clients in async Python routes to avoid blocking event loops;
- minimize client-side components when server components are adequate.

## Technical Stack Decision Defaults

Legacy technical-stack notes are reference inputs, not current authority. Bucky packets should choose stack rules from the live repo first, then apply these defaults only when the repo is silent:

- prefer boring, maintainable stack choices over novelty;
- keep secrets and provider keys server-side only;
- document runtime assumptions in the project packet before implementation;
- add validation and logging around agent/runtime boundaries;
- treat generated dashboards, local DBs, logs, and cache files as runtime artifacts unless the repo explicitly tracks them;
- verify dependency, framework, and provider versions from current project files or official docs before presenting them as current.

## Bucky Dispatch Rule

For security, payment, auth, deployment, public release, or customer-data tasks, Bucky packets must include:

```yaml
risk_level:
approval_required:
forbidden_actions:
secret_handling:
log_policy:
verification:
rollback_or_recovery:
```
