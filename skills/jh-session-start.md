---
type: skill
title: Jh Session Start
name: jh-session-start
triggers:
  - 세션 시작
  - 이어서 진행
  - 재개
  - 이전 작업 확인
description: JH 세션 시작 시 컨텍스트 복원 절차. 이전 작업 상태를 brain에서 가볍게 복원한다.
ingested_via: 'mcp:put_page'
ingested_at: '2026-06-22T17:46:13.173Z'
source_kind: 'mcp:put_page'
tags:
  - context-restore
  - jh-system
  - session
  - skill
---

# JH Session Start — 컨텍스트 복원 스킬

## Contract
- brain recall로 이전 작업 상태를 1회 pull (전체 scan 금지)
- MEMORY.md는 자동 로드됨 — 추가 읽기 없음
- 압축 감지 시 작업 착수 전 전환 권고

## 절차

### 1. 압축 감지 (첫 번째 행동)
"This session is being continued..." 문구 존재 시 즉시 전환 권고. 작업 착수 금지.

### 2. 프로젝트 컨텍스트 복원 (targeted pull)
```
gbrain.recall(entity="<프로젝트명>", limit=5)
→ 최근 결정/버그/패턴만 확인
```
결과는 답변에 직접 활용, context 누적 금지.

### 3. 세션 캡처 확인 (선택)
```
gbrain.query("session-capture <날짜>", limit=1)
→ 지난 세션 완료 상태 확인
```

### 4. 착수
- 이전 세션 메모가 있으면 다음 우선순위 항목부터 시작
- 없으면 사용자 요청 그대로 착수

## 세션 종료 시
```
gbrain.add_timeline_entry(slug="<프로젝트명>", summary="<완료 내용>")
→ 다음 세션을 위한 context breadcrumb 저장
```
