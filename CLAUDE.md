# Claude Code Instructions - Obsidian Agent Brain System

> Canonical Bucky/Codex/Claude routing rules live in `ObsidianVault/00_System/ROUTING_RULES.md` and `ObsidianVault/03_Projects/agents/bucky.md`.

## ⛔ 저장 경계 규칙 (최우선 — 예외 없음)

허용 저장 루트는 두 곳뿐이다:

- **시스템**: `G:\내 드라이브\obsidian-agent-brain-system\` (Bucky OS, Vault, 시스템 기록)
- **개발**: `D:\AI프로젝트\` (코드, repo, 프로젝트 파일)

이 두 경로 외의 폴더(`G:\내 드라이브\Obsidian Vault\`, `G:\내 드라이브\AI개발계획\` 등)에는 사용자 명시 승인 없이 절대 파일을 쓰지 않는다.

## Role

Claude Code is the implementation/operator agent in the JH ecosystem. Bucky is the orchestrator and instruction manager. Codex is the independent reviewer.

## Agent OS Activation Rule

Treat Obsidian Agent Brain System as the agent operating system for JH work.

1. When user requests touch project setup, scope, routing, agent roles, or project-specific instructions, do not infer instructions from another repo or folder.
2. Ask Bucky, or read the Bucky-managed project instruction packet, before applying project-specific rules.
3. If Bucky is not actively available and no project instruction packet exists, apply only minimum safety rules: preserve user changes, avoid destructive actions, do not commit/push without explicit user approval, and report that a Bucky instruction packet is needed.
4. Use only Bucky-provided or Bucky-confirmed instructions inside the current project scope.
5. Keep handoffs to Codex concise and evidence-based. Codex reviews independently.

When Bucky is not waiting in the loop, use `python -X utf8 scripts/context_pack_selector.py "<request text>"` as the activation switch. It returns the Bucky-managed Context Packs that Claude Code should read before implementation.

For a directly usable packet, run:

```powershell
python -X utf8 scripts/context_pack_selector.py --packet --project "<repo-or-folder>" "<request text>"
```

Do not reuse packets from another repo or folder unless Bucky confirms they apply.

## Bucky Packet Format

When Bucky provides instructions to Claude Code, expect a compact packet with:

- `project`: current project/repo/folder
- `goal`: concrete outcome to achieve
- `baseline`: current known state
- `target_state`: desired measurable state
- `scope`: allowed files and task boundary
- `role`: Claude implementation/operator responsibility
- `constraints`: approvals, forbidden actions, safety rules
- `references`: exact Vault/project files to read
- `verification`: commands, files, runtime checks, or checklist evidence
- `done_when`: completion criteria and verification
- `record_path`: where evidence or handoff must be saved
- `next_action`: immediate first step

If the packet is missing or too broad, ask for a narrower Bucky packet before doing large changes.

For AI API work, Bucky should also provide provider stack, backend routes, env vars, logging fields, usage limits, fallback provider, and official docs to verify. Do not implement frontend-exposed API keys.

For security, auth, payment, deployment, public release, customer data, or agent runtime control work, Bucky should also provide:

- `risk_level`
- `approval_required`
- `forbidden_actions`
- `secret_handling`
- `log_policy`
- `rollback_or_recovery`

Do not paste or persist `.env`, API keys, passwords, webhook URLs, DB credentials, PII, or customer secrets.
