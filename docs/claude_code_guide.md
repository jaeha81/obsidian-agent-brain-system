# Claude Code Guide
> Created: 2026-05-22

## Role

Claude Code는 이 시스템의 구현/운영 에이전트다.
파일 생성, 코드 작성, 시스템 설정, AgentBus 처리를 담당한다.

## Session Start Protocol

1. `00_System/AGENT_STATE.md` 읽기 — 현재 상태 확인
2. `00_System/TASKS.md` 읽기 — 현재 작업 목록 확인
3. `10_AgentBus/inbox/` 확인 — 대기 중인 요청 확인
4. 작업 시작 전 `00_System/LOCKS/` 에 잠금 파일 생성

## Session End Protocol

1. 잠금 파일 삭제
2. `AGENT_STATE.md` 업데이트 (current_task 초기화)
3. `TASKS.md` 업데이트 (완료 항목 체크)
4. `HANDOFF_LOG.md` 에 인수인계 기록 추가
5. 완료 보고서 `10_AgentBus/reports/` 에 저장

## Context Rules

- 전체 Vault를 한 번에 읽지 않는다.
- 관련 프로젝트 폴더 (`03_Projects/{name}/`) 와 필요한 파일만 참조한다.
- 읽은 내용은 10줄 이내로 요약 후 핵심만 컨텍스트에 유지한다.

## File Output Rules

| 출력 대상 | 위치 |
|---------|------|
| 구현 코드 | GitHub repo 적절한 폴더 |
| Vault 노트 | ObsidianVault/해당 폴더 |
| AgentBus 결과 | 10_AgentBus/outbox/ClaudeCode/ |
| 완료 보고서 | 10_AgentBus/reports/ |
| 컨텍스트 팩 | 06_Context_Packs/ |

## AgentBus Message Format

```markdown
# Task: {TASK_ID}
- From: ClaudeCode
- To: {Agent}
- Priority: {P0/P1/P2}
- Date: {YYYY-MM-DD}
- Status: {pending/in_progress/completed/failed}

## Request
{내용}

## Context
{필요한 컨텍스트}
```

## Security Checklist

작업 완료 전 반드시 확인:
- [ ] API Key, 비밀번호 포함 여부
- [ ] 기존 CLAUDE.md, wiki/, raw/ 덮어쓰기 여부
- [ ] RAW 데이터 GitHub 커밋 여부
- [ ] ObsidianVault GitHub 커밋 여부
