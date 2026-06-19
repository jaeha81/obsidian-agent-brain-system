---
title: Codex·Claude 분리 운영 패턴
date: 2026-05-28
source: daily-plus/2026-05-28.md (Card 4)
priority: P1
category: knowledge
status: distilled
tags:
- codex
- claude
- orchestration
- planner-executor
- multi-agent
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# Codex·Claude 분리 운영 패턴

> ChatGPT Pulse 2026-05-28 Card 4 증류 (P1 · knowledge)

## 목적
플래너-분석가-오케스트레이터 3단 구성으로 에이전트 협업을 안전하고 결정론적으로 운영하는 방법. CODEGEN(Codex)은 JSON 계획, ANALYST(Claude)는 검증, 오케스트레이터는 라우팅. 각 에이전트의 역할을 명확히 분리해 실수를 최소화하고 검증 가능성을 높임.

## 핵심 내용
- **3단 역할 분리**:
  - **CODEGEN (Codex)**: 코드 생성, 구현, JSON 계획 작성. 단독 배포 권한 없음
  - **ANALYST (Claude)**: 계획 검증, 위험 평가, 실행 승인/거부. 구현 직접 수행 없음
  - **ORCHESTRATOR (Bucky)**: 라우팅, 상태 관리, 두 에이전트 간 메시지 전달
- **JSON 계획 포맷**:
  ```json
  {
    "plan_id": "uuid",
    "created_by": "codex",
    "steps": [
      {"step": 1, "action": "write_file", "path": "...", "sha256": "..."},
      {"step": 2, "action": "run_test", "command": "..."}
    ],
    "rollback": [...]
  }
  ```
- **검증 파이프라인**: Codex 계획 제출 → Claude 검증 (스키마+위험) → Bucky 승인 게이트 → 실행
- **재시도 안전**: 각 step에 idempotency_key 포함, 실패 시 동일 step 재시도 안전

## 구현 체크리스트
- [ ] JSON 계획 스키마 정의 (JSONSchema)
- [ ] Claude 검증 프롬프트 템플릿 작성
- [ ] Bucky 승인 게이트 로직 구현
- [ ] 에이전트 간 메시지 포맷 표준화
- [ ] 롤백 계획 필수 포함 여부 검증

## 관련 컨텍스트
- 검증자와 롤백 템플릿: `2026-05-27-dp-verifier-rollback-template.md`
- JCS 검증용 1줄 스모크: `2026-05-29-dp-jcs-smoke-verifier.md`
- Codex 병행 운영 원칙: Vault Memory `feedback_codex_parallel.md`

## 관련 노트
- [[hubs/JH System]]
