---
type: knowledge-note
date: 2026-05-28
source: daily-plus
category: agent-prompting
tags:
  - "#area/ai_automation"
  - "#status/active"
summary: Gemini 플래너 + Codex 실행자 패턴 — Planner-Executor 구조로 안전하고 결정론적인 에이전트 협업 설계
status: staged
next_action: Bucky 패킷 확인 후 실제 에이전트 프롬프트에 반영
---

# Gemini 플래너, Codex 실행자 패턴

## 목적

**Planner–Executor** 구조로 에이전트 워크플로우를 안전·일관·검증 가능하게 운영하는 설계. Gemini가 계획(JSON), Codex가 실행.

## 아키텍처 개요

```
User Goal
    ↓
PLANNER (Gemini/Claude)
  - 목표 → plan_v1 JSON
  - 최대 7스텝, 의존성 명시
  - 승인 필요 스텝 플래그
    ↓
EXECUTOR (Codex/Claude Code)
  - plan_v1 읽고 담당 스텝 실행
  - done_when 기준으로 검증 후 완료 처리
  - approval_required 스텝은 중단 + 사용자 알림
    ↓
VERIFIER (Bucky/Codex)
  - 각 스텝 결과 검증
  - 실패 시 롤백 또는 에스컬레이트
```

## PLANNER 프롬프트 스니펫

```
You are the Planner agent.
Input: user goal string
Output: plan_v1 JSON only (no prose)
Schema: { steps: [ { id, action, owner, depends_on[], done_when, approval_required? } ] }
Constraint: max 7 steps, prefer atomic actions, no ambiguous steps
```

## EXECUTOR 프롬프트 스니펫

```
You are the Executor agent (role: codex).
Input: plan_v1 JSON
Execute only steps where owner == "codex".
Before marking done: verify done_when condition is met.
Output per step: { step_id, status, evidence_path, next_step }
On approval_required: pause, output { blocked: true, reason, step_id }
```

## plan_v1 JSON 예시

```json
{
  "plan_id": "p-20260528-001",
  "goal": "Wishket 제안서 자동 작성 파이프라인 구축",
  "steps": [
    {
      "id": "s1",
      "action": "Wishket 공고 파싱 스크립트 작성",
      "owner": "codex",
      "depends_on": [],
      "done_when": "스크립트가 공고 JSON 반환하면 완료"
    },
    {
      "id": "s2",
      "action": "제안서 템플릿 생성",
      "owner": "claude",
      "depends_on": ["s1"],
      "done_when": "docs/proposal_template.md 존재"
    }
  ]
}
```

## 적용 시 주의

- 현재 Gemini API 키 미등록 — Gemini 역할은 Claude로 대체 가능.
- 실제 Bucky 운영 프롬프트 변경 전 Bucky 패킷 승인 필요 (staged 상태).
