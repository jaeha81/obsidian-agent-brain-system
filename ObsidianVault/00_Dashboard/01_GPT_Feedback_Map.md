---
type: system-doc
status: active
created: 2026-05-31
owner: Bucky
tags:
  - #status/active
---

# 01 GPT Feedback Map

GPT 채팅 기록 및 오늘의 플러스 피드백 허브.

---

## 목적

매일 쌓이는 GPT 피드백을 분류·연결하여 사업화/자동화 아이디어를 식별한다.

## 연결 폴더

- `04_Wiki/daily-plus/` — ChatGPT Pulse 자동 수집 (메인 소스)
- `07_Reports/` — 운영 리포트
- `04_DAILY_REPORTS/` — 일일 브리핑

## 핵심 태그

`#area/gpt_feedback` `#source/chatgpt` `#source/today_plus`

---

## 핵심 노트

- [[2026-05-30-오늘의-플러스-운영-리포트]] — 오늘의 플러스 운영 현황
- [[20260523_harness_subscription_agent_update]] — Harness 구독 에이전트 업데이트
- [[20260522_init_completion_report]] — Init 완료 리포트

---

## ChatGPT Pulse 일일 수집 (메인)

```dataview
TABLE date AS "날짜", card_count AS "카드수", collection_status AS "상태"
FROM "04_Wiki/daily-plus"
SORT date DESC
LIMIT 14
```

## GPT 피드백 기록 대시보드

```dataview
TABLE file.mtime AS "수정일", summary AS "요약", status AS "상태"
FROM #area/gpt_feedback
SORT file.mtime DESC
LIMIT 20
```

## 최근 운영 리포트

```dataview
LIST
FROM "07_Reports" OR "04_DAILY_REPORTS"
SORT file.mtime DESC
LIMIT 10
```

## 사업화 가능 피드백

```dataview
TABLE summary AS "요약", business_value AS "사업 가치", next_action AS "다음 행동"
FROM #area/gpt_feedback
WHERE business_value = "high"
SORT file.mtime DESC
```
