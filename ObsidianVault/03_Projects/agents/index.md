---
title: Agent Knowledge Base Index
updated: 2026-05-30
owner: Bucky
type: index
tags:
  - #area/business_model
summary: "└─ bucky (오케스트레이터 · 지침 관리자)"
category: business_model
status: active
next_action: review
---

# Agent Knowledge Base

JH 에이전트 생태계의 지식베이스 허브. 각 문서는 역할별로 분류되어 있으며 Bucky Context Pack과 연결된다.

## 에이전트 역할 맵

```
사용자
  └─ [[bucky]] (오케스트레이터 · 지침 관리자)
       ├─ [[../../../scripts/context_pack_selector.py|context_pack_selector]] (발동 스위치)
       ├─ [[codex-instructions]] (독립 검수 · Codex canonical 지침)
       ├─ Claude Code (구현 · 운영)
       └─ AgentBus (결과 큐 · 기록)
```

## 파일 목록

| 파일 | 역할 | 상태 |
|------|------|------|
| [[bucky]] | 오케스트레이터 운영 지침 | canonical |
| [[codex-instructions]] | Codex canonical 운영 지침 | canonical |
| [[roles]] | 에이전트별 경계 정의 | canonical |
| [[onboarding]] | 신규 에이전트 진입 절차 | canonical |
| [[sub-agents]] | 서브에이전트 목록 | 참조 |
| [[agent-house-role-map]] | AgentBus 역할 지도 | 참조 |
| [[rank-system]] | 에이전트 등급 체계 | 참조 |
| [[evolution]] | 에이전트 진화 기록 | 참조 |
| [[COMMON-PHILOSOPHY]] | 공통 운영 철학 | 참조 |

## 핵심 외부 연결

| 연결 | 경로 |
|------|------|
| Context Pack 인덱스 | [[../../06_Context_Packs/index]] |
| Knowledge Path 정책 | [[../../05_Frameworks/guides/knowledge-paths]] |
| Bucky OS 런북 | [[../../00_System/BUCKY_OS_RUNBOOK]] |
| 라우팅 규칙 | [[../../00_System/ROUTING_RULES]] |
| AgentBus 감사 | [[../../00_UPGRADE/agentbus-audits/index]] |
| 검수 자동화 프로토콜 | [[../../00_UPGRADE/review-automation-protocol]] |

## 도구 연결

| 도구 | 용도 |
|------|------|
| `python -X utf8 scripts/context_pack_selector.py "<요청>"` | Context Pack 선택 (Bucky 부재 시 발동 스위치) |
| `python -X utf8 scripts/review_checklist_runner.py start` | 세션 시작 체크 (변경파일 + OPEN 이슈) |
| `python -X utf8 scripts/bucky_os_gate.py --fail-on-error` | 마이그레이션/전역 지침 변경 전 게이트 |
| `python -X utf8 scripts/preflight_check.py` | 시작 점검 |
