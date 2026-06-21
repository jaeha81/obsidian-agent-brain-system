---
type: knowledge
title: Daily Plus source availability guard
date: 2026-06-12
source: daily-plus/2026-06-12.md (Card 1)
source_type: daily-plus-dashboard
owner: distiller
target: 03_Knowledge / 00_UPGRADE
status: approved
priority: P1
approved_by: user
approved_at: 2026-06-12
agent: Bucky
tags:
- daily-plus
- distiller
- fail-safe
- area/ai_automation
- status/approved
- source/today_plus
summary: 공식 Pulse가 404/빈 카드일 때 빈 대시보드를 만들지 않도록 수집 실패를 명확한 운영 이벤트로 차단한다.
next_action: implement
graph_cluster: daily-log
---

# Daily Plus source availability guard

## 개요

공식 ChatGPT Pulse가 404, 로그인 필요, 카드 0개 등으로 접근 불가 상태일 때,
빈 데이터를 정상 수집으로 저장하지 않고 명확한 실패 이벤트로 기록한다.

오늘(2026-06-12) 수집 시 Pulse 404 발생 → 복구 캡처로 대체 (collection_status: fallback)

## 구현 작업 분해

### Task 1. chatgpt_daily_collector.py 가용성 체크 강화
- HTTP 응답 코드 감지 (200 외 → 실패)
- 카드 추출 결과 0개 → 실패로 처리
- 실패 유형 분류: http_error / auth_required / empty_cards / parse_error
- collection_status: fallback 자동 기록 (이미 구현됨, 명시적 분기 추가)

### Task 2. daily_plus_morning_report.py fail-safe 보고
- 빈/오류 캡처 감지 시 needs-attention 보고서 생성
- 기존 정상 대시보드 덮어쓰기 방지
- 실패 원인 + 다음 조치 Discord #jh-오늘의플러스 보고

### Task 3. docs/daily-plus.html 대시보드 가드
- 후보가 있는 날짜만 정상 통계 갱신
- 복구 캡처(collection_status: fallback) 시 황색 경고 배너 표시
- 단순 404 스텁이 대시보드 카드를 덮지 못하도록 생성 전 검증

## 현재 상태

- collection_status: fallback 필드: 이미 오늘 파일에 적용됨 (완료)
- Task 1 명시적 분기: 미구현
- Task 2 fail-safe 보고: 미구현
- Task 3 대시보드 가드: 미구현

## 다음 행동

우선순위 생기면 Bucky 큐로 승격. 구현 착수 시 chatgpt_daily_collector.py → daily_plus_morning_report.py → daily-plus.html 순서로 진행.

## 관련 노트
- [[hubs/JH System]]

[[technical-patterns-hub]]
