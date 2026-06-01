---
title: Routing Rules
updated: 2026-05-30
owner: Bucky
---

# Routing Rules

Bucky is the main orchestrator for JH agent work. Claude Code implements. Codex reviews independently. The user owns final direction and approval.

## Agent Roles

| Agent | Role | Responsibility |
|---|---|---|
| Bucky | Main orchestrator | classify requests, select Context Packs, issue instruction packets, collect results |
| Claude Code | Implementer / operator | code changes, file edits, scripts, local verification |
| Codex | Independent reviewer | review, verification, risk checks, user-facing findings |
| Hermes | AI backend | optional reasoning support for Bucky |
| User | Final decision maker | approval, priority, sensitive decisions |

## Execution Environment

Claude Code와 Codex는 두 가지 환경에서 실행될 수 있다. Bucky는 패킷 발행 시 `env` 필드로 명시한다.

| 환경 | 설명 | 사용 상황 |
|---|---|---|
| `local` | 집 PC 터미널 — `G:\내 드라이브\obsidian-agent-brain-system` 기준 | 파일 수정, git 작업, 스크립트 실행, 빌드/배포 |
| `web-ext` | 웹 브라우저 확장 플러그인 (claude.ai/code 또는 Codex 웹) | 코드 리뷰, 빠른 질의, 브라우저에서 진행 중인 작업 |

### 환경별 제약 사항

**`local` 환경:**
- 파일 시스템 직접 접근 가능 → 파일 수정·저장·커밋·푸시 가능
- 스크립트 실행, Docker, CLI 도구 사용 가능
- Bucky 패킷 전체 실행 가능

**`web-ext` 환경:**
- 파일 시스템 직접 접근 불가 → 코드 제안/리뷰만 가능
- 사용자가 브라우저에서 결과를 보고 로컬에서 직접 적용하거나 Bucky에 전달
- git 작업 불가 — 결과를 Claude Code(local)에 relay 필요

### Bucky 패킷 `env` 필드

```yaml
env: local | web-ext | both
```

- `both`: 동일 작업을 두 환경 모두에서 처리 가능 (예: 리뷰는 web-ext, 실제 적용은 local)
- 생략 시 기본값: `local`

## Routing Flow

```text
User request
  -> Bucky classifies project/task/risk
  -> Bucky selects Context Packs or emits instruction packet
  -> Claude Code implements or Codex reviews
  -> AgentBus records result
  -> User receives final report
```

Direct user requests to Claude Code or Codex are allowed, but if the project is new, the scope is unclear, or no local instruction packet exists, the agent must trigger Bucky guidance first.

## Bucky Activation

Use the selector when Bucky is not actively waiting:

```powershell
python -X utf8 scripts/context_pack_selector.py "<request text>"
```

Use packet mode when an agent needs directly actionable JSON:

```powershell
python -X utf8 scripts/context_pack_selector.py --packet --project "<repo-or-folder>" "<request text>"
```

## Instruction OS Gate

Runbook: `ObsidianVault/00_System/BUCKY_OS_RUNBOOK.md`

Before large migration, cross-project instruction work, global Claude/Codex instruction changes, or new project packet rollout, run:

```powershell
python -X utf8 scripts/bucky_os_gate.py --fail-on-error
```

Startup checks also surface this gate through:

```powershell
python -X utf8 scripts/preflight_check.py
```

The gate must pass before treating legacy material as Bucky-managed context. A passing gate proves current instruction authority, legacy instruction inventory coverage, selector routing, and value-free secret manifest handling.

## Default Context Packs

| Task | Primary pack |
|---|---|
| Review / verification | `ObsidianVault/03_Projects/agents/codex-instructions.md` |
| Implementation | `CLAUDE.md`, `ObsidianVault/03_Projects/agents/bucky.md` |
| Legacy migration | `ObsidianVault/06_Context_Packs/bucky-migration-build-charter.md` |
| Goal Mode / context efficiency | `ObsidianVault/06_Context_Packs/bucky-context-efficiency-goal-mode.md` |
| AI API / model routing | `ObsidianVault/06_Context_Packs/bucky-ai-api-routing-policy.md` |
| Security / runtime | `ObsidianVault/06_Context_Packs/bucky-security-runtime-governance.md` |
| Vault records / ingest | `ObsidianVault/06_Context_Packs/bucky-vault-ingestion-record-policy.md` |
| User/project terrain | `ObsidianVault/06_Context_Packs/bucky-user-project-terrain.md` |
| Design improvement / UI·UX quality | `ObsidianVault/06_Context_Packs/bucky-design-improvement-policy.md` |
| Sync / AgentBus | `ObsidianVault/05_Frameworks/guides/sync-protocol.md`, `ObsidianVault/05_Frameworks/AgentBus/agentbus_protocol.md` |

## Approval Gates

The following require explicit user approval:

- commit or push
- delete, move, archive, reset, force push
- broad Vault scans not required for the direct task
- non-dry-run legacy migration
- production deployment or payment/auth/security changes
- use or exposure of credentials, API keys, customer data, or PII

## Folder Boundary Rules (HARD RULE — No Exceptions Without User Approval)

JH 시스템은 두 개의 루트만 존재한다:

| 루트 | 경로 | 용도 |
|---|---|---|
| **System root** | `G:\내 드라이브\obsidian-agent-brain-system\` | Bucky OS, Vault, AgentBus, Context Packs, 시스템 기록 |
| **Dev root** | `D:\AI프로젝트\` | 개발 프로젝트, 코드, repo, 산출물 |

### 절대 금지

- `G:\내 드라이브\obsidian-agent-brain-system\` 외부에 시스템/Vault 파일 저장 금지
- `D:\AI프로젝트\` 외부에 개발 프로젝트 파일 저장 금지
- `G:\내 드라이브\Obsidian Vault\` (별도 볼트 경로)에 신규 파일 작성 금지
- `G:\내 드라이브\AI개발계획\` 등 비정규 경로에 저장 금지
- 사용자 명시 승인 없이 위 두 루트 외 어떤 폴더도 건드리지 않는다
- **예외**: 사용자가 특정 폴더를 직접 지정하거나 확인을 요청한 경우 → 작업 전 "이 폴더에 접근/수정해도 됩니까?" 승인 확인 후 진행

### 작업 분류 기준

- **시스템 작업** (Bucky OS, Vault 노트, Context Pack, AgentBus 기록, 대시보드) → `G:\내 드라이브\obsidian-agent-brain-system\` 안에 저장
- **개발 작업** (코드, repo, 프로젝트 파일, 빌드 산출물) → `D:\AI프로젝트\` 안에 저장
- 분류가 불명확하면 저장 전에 사용자에게 확인

## Project-Scoped Instructions

1. Project-specific rules apply only inside that project.
2. Do not reuse another repo/folder packet automatically.
3. New projects start with no project-specific packet unless one exists locally.
4. Bucky provides or confirms the packet before project-specific rules are applied.
5. If Bucky is unavailable, agents apply only minimum safety rules and report that a packet is needed.
6. `scripts/bucky_os_gate.py` verifies the new-project packet contract: project boundary, no packet reuse, secret-like archive quarantine, Context Pack references, and verification requirements.

## AgentBus Rules

- Current AgentBus protocol: `ObsidianVault/05_Frameworks/AgentBus/agentbus_protocol.md`
- Use `ObsidianVault/10_AgentBus/` for current queue, outbox, handoff, and task-lock records.
- Do not revive old shared-log paths as active queues.
- Large logs and JSONL files must be searched by date, status, target, or keyword.

## Legacy Handling

Useful legacy rules are compressed into Context Packs. Historical folders and generated global instruction files are not current authority.

Rules:

- Do not read long legacy source files unless a selected Context Pack is insufficient.
- Do not execute legacy scripts unless classified as safe/current and approved.
- Preserve source paths in migration notes for traceability.
- Re-run `scripts/legacy_residue_scanner.py` after cleanup passes.

## Completion Standard

An agent may report completion only when current evidence proves the requested outcome:

- files changed as intended
- relevant command or inspection passed
- risks and blockers are stated
- record/handoff path is saved when required
- no broader claim is made than the evidence supports

## Execution Environment — VS Code Integration (2026-06-02 추가)

Claude Code는 세 가지 실행 환경에서 작동한다:

| env | 설명 | 가능한 작업 |
|-----|------|------------|
| `local` | 터미널(bash/PowerShell) | 파일 수정, git, 스크립트 실행, 배포 |
| `web-ext` | 웹 브라우저 Claude Code/Codex 확장 | 코드 리뷰, 제안, 질의 — 파일 직접 저장 불가 |
| `vscode` | VS Code 내장 Claude Code 확장 | 파일 수정 + VS Code 에디터 컨텍스트 자동 인지 |

### VS Code 컨텍스트 캡처 (터미널 → VS Code 상태 확인)

사용자가 "VS코드 확인해", "VS코드 작업 이어서" 요청 시 Claude Code가 실행하는 절차:

```bash
# 1. 현재 VS Code 상태 캡처
python -X utf8 scripts/vscode_context.py

# 2. JSON 출력 (파싱용)
python -X utf8 scripts/vscode_context.py --json

# 3. VS Code에서 특정 파일 열기
python -X utf8 scripts/vscode_context.py --open "apps/api/main.py:42"
```

`scripts/vscode_context.py`는:
- 현재 활성 VS Code 워크스페이스 경로 반환
- VS Code History에서 최근 편집 파일 목록 반환
- 워크스페이스 내 최근 수정 파일 목록 반환

### Bucky 패킷 env 필드

패킷 발행 시 `env` 필드를 명시한다:

```yaml
env: local          # 터미널에서 실행
env: web-ext        # 웹 확장에서 실행 (파일 수정 불가)
env: vscode         # VS Code 내 확장에서 실행
env: vscode+local   # VS Code 확장 + 터미널 병행
```

env가 `web-ext`인 경우 Claude/Codex는 파일 직접 저장·git 작업을 수행하지 않고 제안·리뷰만 제공한다.

## ⛔ 완료 보고 증거 강제 규칙 (HARD RULE — 2026-05-30 추가)

**배경**: Bucky가 실제 도구 실행 없이 완료를 선언한 허위보고 패턴이 반복 확인됨 (JH-SHARED 이동은 archive-only / not current operating authority, Gate 1 registry repair 등).

### 완료 보고 금지 조건

- 도구 실행 결과(파일 경로 + ls / cat / query 출력)를 첨부하지 않은 완료 선언 금지
- "완료했습니다" 단독 문장으로 끝나는 보고 금지
- 실행 전 상태와 실행 후 상태를 비교하지 않은 보고 금지

### 완료 보고 필수 포함 항목

모든 작업 완료 보고에는 아래를 반드시 포함한다:

```
작업: <무엇을 했는지>
증거:
  - <실행한 명령어 또는 도구>
  - <실제 출력 결과 (경로, 카운트, 파일 내용 일부)>
실행 전: <이전 상태>
실행 후: <현재 상태>
미완료 항목: <이번에 하지 못한 것, 있으면 명시>
```

### 허위보고 발생 시 처리

- 허위보고가 확인된 작업은 즉시 "미완료"로 재분류
- 재보고 시 위 형식으로 실제 증거를 다시 제출
- 이전 완료 보고를 번복할 때는 번복 이유와 실제 상태를 명시
