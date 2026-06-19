---
title: Three Scalable Orchestration Patterns
date: 2026-06-11
source: daily-plus/2026-06-10.md (Card 11)
priority: P3
category: knowledge
status: distilled
tags:
- orchestration
- multi-agent
- conductor
- pipeline
- market
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# Three Scalable Orchestration Patterns

> ChatGPT Pulse 2026-06-10 Card 11 증류 (P3 · knowledge-candidate)

## 목적

멀티 에이전트 시스템 설계 시 적용 가능한 3가지 오케스트레이션 패턴. 실제 시스템은 이들을 혼합한다.

## 패턴 1: Conductor (중앙 계획형)

```
Conductor
├── Task A → Agent 1
├── Task B → Agent 2
└── Task C → Agent 3 (depends on A)
```

- **특징**: 명확한 단계/의존성, 단일 감사 증적
- **장점**: 예측 가능, 디버깅 용이
- **약점**: 단일 실패점 (Conductor 장애 시 전체 중단)
- **적합**: Bucky → Claude Code / Codex 패턴

## 패턴 2: Market (입찰형)

```
Task Dispatcher
├── Agent A (bid: 2s, cost: $0.01)
├── Agent B (bid: 5s, cost: $0.003)
└── Agent C (bid: 1s, cost: $0.02)  ← 선택됨
```

- **특징**: 여러 에이전트 경쟁, 비용 제어
- **장점**: 유연성, 부하 분산
- **약점**: 스키마 편차 위험 (각 에이전트 출력 형식 불일치)
- **적합**: 병렬 리서치, 다중 제공자 AI 라우팅

## 패턴 3: Pipeline (단계 변환형)

```
Input → Stage 1 → Stage 2 → Stage 3 → Output
```

- **특징**: 안정적 반복, 병렬화 가능
- **장점**: 높은 처리량, 단순한 오류 격리
- **약점**: 역압력 처리 필요 (느린 스테이지가 전체 차단)
- **적합**: Pulse → 증류 → Obsidian 저장 파이프라인

## 혼합 적용 예시

```
Conductor over Pipeline:
  Bucky (Conductor)
  └── Daily Plus Pipeline
      ├── 수집 Stage
      ├── 분류 Stage
      └── 저장 Stage

Market inside Stage:
  AI 라우팅 스테이지 내부에서
  Claude/GPT/Gemini 입찰 선택
```

## 공통 안전 장치

- JSON 스키마 계약 (에이전트 간 출력 형식 표준화)
- 감사 증적 로그 (append-only)
- 역압력 제어 (큐 크기 제한)
- 격리 실패 (커넥터 장애가 전체 런타임에 영향 없도록)

## JH 시스템 적용 현황

| 컴포넌트 | 패턴 |
|---------|-----|
| Bucky → Claude/Codex | Conductor |
| Daily Plus 파이프라인 | Pipeline |
| AI API 라우팅 | Market |
| AgentBus 디스패처 | Conductor + Pipeline 혼합 |

## 관련 노트
- [[hubs/JH System]]
