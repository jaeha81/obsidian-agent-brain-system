# Claude Code Instructions - Obsidian Agent Brain System

> Canonical Bucky/Codex/Claude routing rules live in `ObsidianVault/00_System/ROUTING_RULES.md` and `ObsidianVault/03_Projects/agents/bucky.md`.

## ⛔ 세션 관리 규칙 (최우선 — 모든 프로젝트 공통 / 전역 CLAUDE.md와 동일)

세션 효율이 작업 진행보다 반드시 우선한다. 과도한 세션 압축은 작업 품질을 저하시킨다.

### 1. 세션 시작 시 — 압축 여부 확인 (첫 번째 행동)

압축 감지 조건 (하나라도 해당하면 즉시 새 세션 전환 권고):
- "This session is being continued from a previous conversation that ran out of context" 문구 존재
- 이전 대화 내용이 요약문으로 대체되어 있음

**감지 시 즉시 실행 (작업 착수 전)**:
1. 사용자에게 세션 압축 감지를 알린다
2. `ObsidianVault/00_System/HANDOFF_LOG.md`에 현재 상태 기록
3. 다음 세션용 붙여넣기 명령어 제공
4. **작업을 시작하지 않는다** — 사용자가 "계속해"라고 해도 전환 먼저

### 2. 세션 진행 중 — 사전 예방 (압축 전 분리)

다음 징후가 보이면 현재 작업 완료 후 즉시 세션 전환을 권고한다:
- 대형 파일 다수 읽기 / 긴 tool 결과가 여러 번 누적됨
- 같은 주제를 20턴 이상 이어서 진행 중
- computer-use 스크린샷이 5개 이상 누적됨

**예방 전환 시 실행**:
1. 현재 작업 단위를 마무리 짓는다
2. 완료 상태와 다음 우선순위를 `HANDOFF_LOG.md`에 기록
3. "세션이 길어지고 있습니다. 새 세션으로 전환을 권고합니다" + 명령어 제공

### 3. 세션 전환 명령어 형식

```
이전 세션 메모: <메모 파일명>
완료: <이번 세션 완료 내용 1~3줄>
다음 우선순위:
1. [P0] ...
2. [P1] ...
```

## ⛔ 저장 경계 규칙 (최우선 — 예외 없음)

허용 저장 루트는 두 곳뿐이다:

- **시스템**: `G:\내 드라이브\obsidian-agent-brain-system\` (Bucky OS, Vault, 시스템 기록)
- **개발**: `D:\AI프로젝트\` (코드, repo, 프로젝트 파일)

이 두 경로 외의 폴더(`G:\내 드라이브\Obsidian Vault\`, `G:\내 드라이브\AI개발계획\` 등)는 archive-only / not current operating authority이며, 사용자 명시 승인 없이 절대 파일을 쓰지 않는다.

**예외**: 사용자가 특정 폴더를 직접 지정하거나 확인을 요청한 경우, 해당 작업 전에 "이 폴더에 접근/수정해도 됩니까?" 라고 승인을 받은 후 진행한다.

## ⛔ 완료 보고 증거 강제 규칙 (최우선)

도구 실행 결과(파일 경로 + ls / query 출력) 없는 "완료" 선언 절대 금지.

모든 완료 보고 필수 형식:
```
작업: <무엇을 했는지>
증거: <실행 명령어> → <실제 출력>
실행 전: <이전 상태>
실행 후: <현재 상태>
미완료: <못 한 것 명시>
```

## Role

Claude Code is the implementation/operator agent in the JH ecosystem. Bucky is the orchestrator and instruction manager. Codex is the independent reviewer.

## Agent OS Activation Rule

Treat Obsidian Agent Brain System as the agent operating system for JH work.

1. When user requests touch project setup, scope, routing, agent roles, or project-specific instructions, do not infer instructions from another repo or folder.
2. Ask Bucky, or read the Bucky-managed project instruction packet, before applying project-specific rules.
3. If Bucky is not actively available and no project instruction packet exists, apply only minimum safety rules: preserve user changes, avoid destructive actions, do not commit/push without explicit user approval, and report that a Bucky instruction packet is needed.
4. Use only Bucky-provided or Bucky-confirmed instructions inside the current project scope.
5. Keep handoffs to Codex concise and evidence-based. Codex reviews independently.

If the user already provided exact files, commands, execution order, or forbidden actions, treat that request as the active Bucky packet for the first step. Run the first requested command before reading plans, broad diffs, whole large files, memories, or unrelated repo state.

Do not call any selector on the hot path for explicit tasks. In this Windows/Google Drive runtime, starting Python or script files can be delayed enough to waste a full turn.

When Bucky is not waiting in the loop and packet selection is actually needed for an unclear or new-project task, use the no-Python fast selector first:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/context_pack_selector_fast.ps1 -Project "<repo-or-folder>" "<request text>"
```

Use the Python selector only when the fast selector is unavailable or deeper routing is explicitly needed. On this Windows/Google Drive setup, Python startup can be slow enough to waste a full turn.

For a directly usable packet, run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/context_pack_selector_fast.ps1 -Project "<repo-or-folder>" "<request text>"
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

## VS Code Context Activation

사용자가 "VS코드 확인", "VS코드 작업 이어서", "VS코드에 들어가" 등을 요청하면 즉시 실행:

```bash
python -X utf8 scripts/vscode_context.py
```

출력에서 `active_workspace`와 `recent_edited_files`를 읽어 현재 작업 맥락을 파악한 뒤 답변한다.

특정 파일을 VS Code에서 열어야 할 때:

```bash
python -X utf8 scripts/vscode_context.py --open "경로/파일.py:라인번호"
```

## Karpathy 코딩 가이드라인 (항상 적용)

> 출처: [Andrej Karpathy의 LLM 코딩 함정 관찰](https://x.com/karpathy/status/2015883857489522876). 전체 스킬: `.claude/skills/karpathy-guidelines/SKILL.md`.
> 트레이드오프: 속도보다 신중함을 우선한다. 사소한 작업엔 판단껏 적용.

### 1. 코딩 전에 생각하라 — 가정·혼란을 숨기지 마라

- 가정은 명시한다. 불확실하면 묻는다.
- 해석이 여러 개면 조용히 하나 고르지 말고 모두 제시한다.
- 더 단순한 방법이 있으면 말한다. 필요하면 반박한다.
- 불명확하면 멈추고 무엇이 혼란스러운지 짚은 뒤 묻는다.

### 2. 단순함 우선 — 문제를 푸는 최소 코드, 추측성 구현 금지

- 요청하지 않은 기능·추상화·유연성/설정성·불가능 시나리오 예외처리 금지.
- 200줄이 50줄로 가능하면 다시 쓴다.
- "시니어 엔지니어가 과하다고 할까?" → 그렇다면 단순화.

### 3. 외과적 변경 — 건드릴 것만 건드리고, 네가 만든 것만 정리하라

- 기존 코드의 인접 부분·주석·포맷을 "개선"하지 마라.
- 망가지지 않은 걸 리팩토링하지 마라. 기존 스타일에 맞춰라.
- 무관한 데드코드는 언급만 하고 삭제하지 마라.
- 단, 내 변경으로 못 쓰게 된 import·변수·함수는 제거한다.
- 기준: 바뀐 모든 줄이 사용자의 요청으로 직접 추적돼야 한다.

### 4. 목표 기반 실행 — 성공 기준을 정하고 검증될 때까지 반복

- "검증 추가" → "잘못된 입력 테스트를 쓰고 통과시킨다"
- "버그 수정" → "재현 테스트를 쓰고 통과시킨다"
- "X 리팩토링" → "전후 테스트 통과를 보장한다"
- 다단계 작업은 `단계 → 검증` 형식으로 간단한 계획을 먼저 제시한다.
