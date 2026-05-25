---
type: synthesis
updated: 2026-04-27
tags: [overview, jh-brain, dev-vault]
---

# JH 개발 볼트 — 위키 합성 개요

> 마지막 업데이트: 2026-04-27 | 페이지: 5개 | 소스: 0개 (시드 단계)

---

## 현재 이해

JH 개발 생태계는 **재하님의 두 번째 뇌**를 구현하는 시스템이다. 중심은 [[entity-jh-brain-system]] — Claude Code 위에서 실행되는 에이전트 오케스트레이터이며, [[entity-mneme]]가 마스터 에이전트로 전체를 통괄한다.

개발 볼트의 핵심 아이디어는 **복리 지식 축적**: 세션이 반복될수록 에이전트들이 더 강해지고, 패턴이 검증되고, 결정이 누적된다.

---

## 핵심 구성요소

### 에이전트 생태계
[[entity-agent-ecosystem]] 참조. JH Brain System은 단일 AI가 아닌 역할 분리된 에이전트 구조로 운영된다. 므네메(마스터)가 총괄하고, 서브 에이전트들(아고니스·아르키·재하·카이·에어라·기르)이 각자 역할을 수행한다.

### 개발 철학
[[concept-agent-philosophy]] 참조. 모든 에이전트는 5원칙을 공유한다: 미래 지향, 진화 의무, 지식베이스 우선, 같은 실수 금지, 진화 기록.

### 개발 워크플로우
[[concept-dev-workflow]] 참조. 0~8단계 체계로 기획 검증 → 리서치 → 계획 → 승인 → 구현 → 배포 → 회고 순으로 진행. "일단 만들고 수정" 방식 금지.

---

## 시스템 경계

| 시스템 | 역할 |
|--------|------|
| **이 위키** | 개발 패턴·결정·에이전트 지식 복리 축적 |
| **OBSIDIAN-SECOND wiki** | 개념·LLM 지식·전략 복리 축적 |
| **AGENT_MEMORY.md** | 현재 세션 진행 상태 (휘발성) |
| **05_Logs/daily/** | 세션별 회고 원본 (RAW) |

---

## 현재 공백 (채워야 할 것)

- 검증된 코드 패턴 없음 → 세션 로그 ingest 시 `pattern-*.md` 생성 필요
- 아키텍처 결정 기록 없음 → `02_Architecture/` ingest 시 `decision-*.md` 생성 필요
- 에이전트별 성과 기록 없음 → `rank-system.md` ingest 필요

---

## 관련 페이지
- [[index]] — 전체 카탈로그
- [[entity-jh-brain-system]] — 시스템 상세
- [[entity-mneme]] — 마스터 에이전트
- [[entity-agent-ecosystem]] — 에이전트 전체 맵
- [[concept-agent-philosophy]] — 공통 철학
- [[concept-dev-workflow]] — 개발 워크플로우
