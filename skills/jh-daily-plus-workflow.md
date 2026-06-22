---
type: skill
title: Jh Daily Plus Workflow
name: jh-daily-plus-workflow
triggers:
  - 오늘의플러스
  - daily plus
  - ChatGPT Pulse
  - 오늘의 플러스 확인
  - daily-plus 처리
description: 오늘의플러스 수집→처리→진화 표준 절차. ChatGPT Pulse 기반 Daily Plus 운영 루프.
ingested_via: 'mcp:put_page'
ingested_at: '2026-06-22T17:47:02.684Z'
source_kind: 'mcp:put_page'
tags:
  - daily-plus
  - evolution-loop
  - gbrain
  - jh-system
  - skill
---

# JH Daily Plus Workflow — 진화루프 스킬

## 시스템 구조
```
ChatGPT Pulse (매일 자동 수집)
  → ObsidianVault/04_Wiki/daily-plus/{date}.md
  → scripts/daily_plus_morning_report.py (09:00 처리)
  → docs/daily-plus.html (대시보드)
  → Discord #jh-오늘의플러스 (릴레이)
  → gbrain timeline entry (진화루프 기록) ← 2026-06-23 추가
```

## 매일 09:00 자동 실행 내용
1. ChatGPT Pulse 카드 수집 확인
2. 대시보드 생성 (`docs/daily-plus.html`)
3. Bucky 아웃박스 메시지 작성
4. Discord 채널 전송
5. **gbrain timeline entry 저장** (candidates/applied/status)

## 수동 재실행 (수집 실패 시)
```powershell
cd "G:\내 드라이브\obsidian-agent-brain-system\scripts"
python -X utf8 daily_plus_morning_report.py
```

## gbrain에서 daily-plus 이력 조회
```
gbrain.query("daily-plus", recency="on", limit=7)
→ 최근 7일 Daily Plus 현황 확인
```

## 문제 상황
- `needs-attention` 상태: ChatGPT Pulse 로그인 만료 → chatgpt.com 재로그인
- 카드 0개: collector 실행 확인 (`scripts/chatgpt_daily_collector.py`)
- Discord 미전송: bot 상태 확인 + 아웃박스 폴링 확인

## 진화루프 연결 확인
```
gbrain.recall(entity="daily-plus/YYYY-MM-DD")
→ 해당 날짜 timeline entry 존재 여부 확인
```
