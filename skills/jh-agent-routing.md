---
type: skill
title: Jh Agent Routing
name: jh-agent-routing
triggers:
  - 에이전트 라우팅
  - 누가 해야 하나
  - Bucky 써야 하나
  - Codex 검수
  - 역할 분담
description: JH 에이전트 역할 분담 및 라우팅 결정 기준. Claude/Codex/Bucky 언제 누구를 쓸지.
ingested_via: 'mcp:put_page'
ingested_at: '2026-06-22T17:46:38.495Z'
source_kind: 'mcp:put_page'
tags:
  - agent
  - bucky
  - claude
  - codex
  - jh-system
  - routing
  - skill
---

# JH Agent Routing — 역할 분담 스킬

## 에이전트 역할

| 에이전트 | 역할 | 하지 않는 것 |
|---|---|---|
| **Claude Code** | 구현·운영·파일 수정·스크립트 실행 | 독립 검수, 오케스트레이션 |
| **Codex** | 독립 검수·리뷰·보안 감사 | 코드 수정(사용자 지시 시 제외), 배포 |
| **Bucky** | 오케스트레이션·Context Pack·지시 패킷 발행 | 직접 구현 |

## 라우팅 결정 트리

```
명시적 명령(파일/명령어 지정)?
  → YES: Claude Code 즉시 실행
  → NO ↓

보안·인증·배포·결제·customer data 포함?
  → YES: Bucky 패킷 먼저 (Tier 3)
  → NO ↓

새 기능 구현 또는 설계 결정 필요?
  → YES: 마이크로 플랜 → 사용자 승인 → Claude 구현 → Codex 검수
  → NO: Claude Code 직접 착수
```

## Codex 검수 필수 트리거
- 새 기능 구현 완료
- 버그 수정 완료  
- API 키·환경변수 변경
- 배포 전 최종 확인
- 보안 관련 코드 수정

## Bucky 패킷 필수 트리거
- 새 프로젝트 초기 설정
- 역할/지침 변경
- 광범위한 마이그레이션
- 명시적 "Bucky에게 물어봐" 요청

## 지침 파일 위치
- `ObsidianVault/00_System/ROUTING_RULES.md` — 정본
- `ObsidianVault/03_Projects/agents/bucky.md` — Bucky 운영 규칙
- `C:\Users\user1\.codex\AGENTS.md` — Codex 역할 정의
