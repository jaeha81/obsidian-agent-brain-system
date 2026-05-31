---
type: context-pack
status: active
created: 2026-05-30
owner: Bucky
source:
  - ObsidianVault/09_Archive/migration-conflicts/2026-05-24/_organized/needs-merge/Obsidian-Vault/wiki/concept-dev-workflow.md
  - ObsidianVault/03_Knowledge/bridges/01_raw-memories-02_dev_workflow-md.md
tags:
  - #area/ai_automation
  - #status/active
---

# Bucky Development Workflow Policy

## Purpose

This pack promotes useful development workflow rules from legacy material into the current Obsidian Agent Brain System. It is for Bucky packets that dispatch implementation, refactor, debugging, QA, or release work.

## Task Size Routing

| Size | Criteria | Handling |
|---|---|---|
| Small | one file, obvious bugfix, copy/style tweak, narrow config change | implement directly, then verify |
| Medium | feature addition, API change, 2-5 files, behavior change | write a short plan or Bucky packet, then implement after scope is clear |
| Large | architecture change, DB schema, deployment, multi-agent work, broad migration | require explicit plan, approval gates, task locks, and independent review |

If size is unclear, treat it as medium until evidence proves it is small.

## Plan-First Rule

For medium and large work, Bucky should provide or request:

```yaml
goal:
scope:
allowed_files:
excluded_files:
approval_gates:
verification:
done_when:
record_path:
```

Do not use planning as a delay tactic. The plan must reduce risk, clarify scope, or define verification.

## Implementation Loop

```text
understand current state
-> make the smallest aligned change
-> run targeted verification
-> record evidence
-> ask for review or continue only if the goal requires it
```

Do not claim completion from partial progress, intent, or a green check that does not cover the requested behavior.

## Verification Defaults

- Code changes: run the narrow existing test/build/typecheck that covers the touched area.
- Frontend changes: verify rendered behavior when a local browser/dev server check is practical.
- Runtime errors: fix the direct visible failure first, verify one response, then stop unless the user expands scope.
- Security/auth/payment/deployment: require explicit approval and use `bucky-security-runtime-governance.md`.
- Migration/legacy absorption: run residue/inventory scans and update audit notes.

## Role Separation

- Claude Code implements.
- Codex reviews independently for risky or user-facing changes.
- Bucky coordinates and keeps the packet small.
- The user approves destructive, public, financial, credential, or broad migration actions.

## Handoff Evidence

For non-trivial work, save or report:

- changed files
- verification commands and results
- unresolved risks
- next action
- record path in Vault or AgentBus when persistence is required

## Legacy Replacement

Old “Plan First” rules are now applied through Bucky packets. They do not authorize broad prework, full-vault rereads, or automatic commit/push.
