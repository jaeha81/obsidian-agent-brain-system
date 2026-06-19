---
title: Minimal Agent Telemetry Signals
date: 2026-06-11
source: daily-plus/2026-06-10.md (Card 10)
priority: P1
category: verification
owner: codex
status: auto-implemented
tags:
- - daily-plus
- auto-implemented
- minimal
- agent
- telemetry
- signals
graph_cluster: daily-practice
---

# Minimal Agent Telemetry Signals

> ChatGPT Pulse 2026-06-10 Card 10 자동 증류 (P1 · verification)

## 목적

5가지 신호를 추적합니다: 레이턴시(p95 > 2

## 핵심 내용

5가지 신호를 추적합니다: 레이턴시(p95 > 2.0s 경고), 토큰(주 기준선 대비 +30% 경고), 입력 신뢰도(< 0.85 경고), 출력 신뢰도(검증 통과율 < 97%), 사용자 승인(< 80%). 최소 이벤트
 스키마는 ts, app, latency_ms, tokens, input_conf, output_conf, approval을 포함합니다. 오늘 상태(p95, 검증%, 승인%)...

## 적용 방법

Turn checks into a repeatable verification checklist before implementation.

## 관련 영역

- 대상: `00_UPGRADE/review-automation-protocol.md`
- 담당: codex
