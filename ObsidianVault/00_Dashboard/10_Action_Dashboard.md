---
type: system-doc
status: active
created: 2026-05-31
owner: Bucky
tags:
  - #status/active
---

# 10 Action Dashboard

오늘 실행해야 할 항목 전체 조회.

---

## 전체 실행 대기

```dataview
TABLE category AS "분류", summary AS "요약", priority AS "우선순위", next_action AS "다음 행동"
FROM ""
WHERE status = "inbox" OR status = "review_needed" OR status = "active"
SORT priority ASC, file.mtime DESC
LIMIT 30
```

## AI 자동화 실행 항목

```dataview
TABLE summary AS "요약", automation_value AS "자동화 가치", next_action AS "다음 행동"
FROM #area/ai_automation
WHERE status != "archive" AND status != "completed"
SORT file.mtime DESC
```

## 사업화 가능 아이디어

```dataview
TABLE category AS "분류", summary AS "요약", business_value AS "사업 가치", automation_value AS "자동화 가치", next_action AS "다음 행동"
FROM ""
WHERE business_value = "high" OR automation_value = "high"
SORT file.mtime DESC
LIMIT 20
```

## 오늘 검토할 노트 (최근 수정)

```dataview
TABLE summary AS "요약", status AS "상태", next_action AS "다음 행동"
FROM ""
WHERE status = "review_needed"
SORT file.mtime DESC
LIMIT 15
```
