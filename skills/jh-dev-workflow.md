---
type: skill
title: Jh Dev Workflow
name: jh-dev-workflow
triggers:
  - 개발 착수
  - 기능 구현
  - 버그 수정
  - PR 생성
  - 코드 작업
description: JH 개발 표준 워크플로우. 착수→구현→검수→완료 보고의 전체 흐름.
ingested_via: 'mcp:put_page'
ingested_at: '2026-06-22T17:46:23.101Z'
source_kind: 'mcp:put_page'
tags:
  - codex
  - dev
  - jh-system
  - skill
  - workflow
---

# JH Dev Workflow — 개발 표준 스킬

## Contract
- 명시적 명령(파일·명령어 지정)이면 즉시 실행
- 불명확하면 마이크로 플랜 제시 후 승인 요청
- 완료 후 반드시 Codex 검수 요청

## 3-Tier 실행 경로

### Tier 1: 명시적 명령 (즉시 실행)
파일·명령어·실행 순서가 지정된 경우:
→ 즉시 실행. 플랜·Context Pack·diff 읽기 없음.

### Tier 2: 일반 구현 (마이크로 플랜)
```
1. 마이크로 플랜 작성 (3~5줄)
2. 사용자 승인
3. 구현
4. Codex 검수 요청
```

### Tier 3: Bucky 필수 (보안·배포·결제)
→ Context Pack 선택 후 Bucky 패킷 대기

## 완료 보고 형식 (증거 필수)
```
작업: <무엇을 했는지>
증거: <실행 명령어> → <실제 출력>
실행 전: <이전 상태>
실행 후: <현재 상태>
미완료: <못 한 것>
```

## Brain 연동 (선택적)
- 반복 패턴/버그 발견 시: `gbrain.add_timeline_entry()` 로 기록
- 다음 세션 recall 대상이 되는 결정만 저장 (모든 작업 저장 아님)

## Dev 폴더 지침
`D:\AI프로젝트\CLAUDE.md` — Karpathy 가이드라인 + Codex 트리거 + 절대 금지 사항
