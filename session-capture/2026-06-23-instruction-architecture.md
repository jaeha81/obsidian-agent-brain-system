---
type: session-capture
title: 2026 06 23 Instruction Architecture
date: '2026-06-23T00:00:00.000Z'
status: completed
ingested_via: 'mcp:put_page'
ingested_at: '2026-06-22T17:03:35.296Z'
source_kind: 'mcp:put_page'
tags:
  - claude-code
  - codex
  - evolution-loop
  - gbrain
  - instruction-architecture
---

# 세션 2026-06-23 — 3계층 지침 분리 + 진화루프

## 완료 작업

| 파일 | 변경 | 효과 |
|---|---|---|
| `C:\Users\user1\.claude\CLAUDE.md` | Agent OS 섹션 제거, 포인터 추가 | 122→102줄 |
| `MEMORY.md` | 세션 로그 49항목 제거 | 93→44줄 |
| `C:\Users\user1\.codex\AGENTS.md` | 세션 관리(15턴/3회) + Brain-First 프로토콜 | Codex 세션 관리 최초 적용 |
| `D:\AI프로젝트\CLAUDE.md` | 신규 생성 | 개발 40개 프로젝트 공통 지침 상속 |
| `scripts/daily_plus_morning_report.py` | `_try_gbrain_timeline()` 추가 | 오늘의플러스→gbrain 진화루프 연결 |

## 3계층 구조 확립

```
Global CLAUDE.md  → 절대 불변 규칙만 (세션/저장/보고/역할)
Project CLAUDE.md → Brain-system 전용 (Vault, Bucky, Knowledge Loop)
D:\AI프로젝트\CLAUDE.md → 개발 공통 (Karpathy, 워크플로우, 진화루프)
  └── 각 프로젝트 CLAUDE.md → 기술스택·스코프만 오버라이드
```

## 다음 세션 우선순위

1. [P1] Project CLAUDE.md(brain system)에서 Global 중복 섹션 정리 (세션관리·저장경계 중복 제거)
2. [P1] gbrain skillpack 5개 실질 콘텐츠 채우기 (현재 content 비어있음)
3. [P2] 40개 기존 프로젝트 CLAUDE.md에서 공통 내용 → `D:\AI프로젝트\CLAUDE.md` 위임 처리
4. [P2] 오늘의플러스 진화루프 첫 동작 확인 (09:00 자동 실행 후 gbrain timeline 확인)
