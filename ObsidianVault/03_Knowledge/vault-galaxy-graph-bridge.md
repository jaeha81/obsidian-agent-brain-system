---
title: Vault Galaxy Graph — 지식 연결 허브 (MOC)
created: 2026-06-07
tags:
- moc
- graph
- knowledge-bridge
- galaxy
- area/research
- status/active
category: knowledge
status: active
summary: 03_Knowledge, 04_Wiki, 00_System의 핵심 노드를 연결하는 Map of Content. Galaxy Graph
  시각화를 위한 허브 노드.
graph_cluster: misc
---

# Vault Galaxy Graph — 지식 연결 허브

> 이 노트는 Obsidian Galaxy Graph의 중심 허브 노드입니다.
> 고립된 클러스터들을 연결해 star cluster 형태의 지식 그래프를 만듭니다.

---

## 시스템 코어

- [[jh-system]] — JH 통합 구축 시스템 브리핑
- [[ROUTING_RULES]] — 에이전트 라우팅 규칙
- [[MASTER_PLAN]] — 전체 마스터 플랜
- [[BUCKY_STATUS]] — Bucky 런타임 상태

---

## Bucky 진화 파이프라인

- [[bucky-evolution-roadmap]] — P0→P3 자가 진화 로드맵
- [[bucky-evolution-pipeline]] — STT + NLP + 패턴 추출 파이프라인
- [[bucky-evolution-session-20260525]] — 진화 세션 기록
- [[bucky-evolution-nlp-layer]] — NLP 레이어 설계
- [[pattern-extractor]] — 반복 패턴 감지 → 스킬 자동 생성
- [[knowledge-auto-capture]] — 대화 → Obsidian 자동 기록

---

## 자동화 & 캡처

- [[webhook-vault-write-pattern]] — 웹훅 기반 Vault 쓰기 패턴
- [[vibe-coding-pipeline]] — AI 보조 개발 24분 파이프라인
- [[typeless-voice-stt-analysis]] — 음성 STT 분석
- [[video-pipeline-checklist]] — 영상 파이프라인 체크리스트
- [[ibujang-api-contract-and-handoff]] — API 계약 핸드오프

---

## 지식 네트워크

- [[github-repo-catalog]] — GitHub 레포 카탈로그
- [[github-catalog]] — 전체 GitHub 카탈로그
- [[법률-노드-정리-플랜]] — 법률 지식 노드 구조화 계획
- [[bucky-evolution-roadmap]] · [[jh-system]] · [[vibe-coding-pipeline]]

---

## InfraNodus 갭 분석 (2026-06-07)

InfraNodus 분석으로 발견된 주요 갭 3개 — 이 노드로 브릿지 완성:

| 갭 | 연결 전 | 연결 후 |
|----|---------|---------|
| Gap 1 | 지식개발 ↔ 자동캡처 | [[bucky-evolution-roadmap]] ↔ [[knowledge-auto-capture]] |
| Gap 2 | 코드검수 ↔ 지식개발 | [[jh-system]] ↔ [[bucky-evolution-pipeline]] |
| Gap 3 | 패턴감지 ↔ 코드검수 | [[pattern-extractor]] ↔ [[bucky-evolution-roadmap]] |

---

## 04_Wiki 허브

- [[jh-system]] · [[overview]] · [[roles]] · [[onboarding]]
- [[concept-dev-workflow]] · [[concept-infranodus-graph-knowledge-base]]
- [[source-llm-wiki-pattern]]

---

## 10_AgentBus — 에이전트 운영 레이어

- [[10_AgentBus/index|AgentBus 허브]] — 에이전트 간 메시지 라우팅 총괄
- [[10_AgentBus/completed/index|완료 태스크 기록]] — BUILD/ANALYZE/EXPLAIN 완료 로그
- [[10_AgentBus/inbox/index|수신 큐]] — Discord → Vault 인입 메시지
- [[10_AgentBus/outbox/index|발신 큐]] — Vault → 에이전트 지시
- [[10_AgentBus/handoffs/index|핸드오프 로그]] — Claude ↔ Codex 핸드오프 기록

---

## 05_Frameworks

- [[Graphify]] — 그래프 시각화 프레임워크
- [[LegalizeKR]] — 법률 지식 처리 프레임워크
