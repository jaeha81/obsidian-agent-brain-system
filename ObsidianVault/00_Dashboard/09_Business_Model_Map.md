---
type: system-doc
status: active
created: 2026-05-31
owner: Bucky
tags:
  - #status/active
---

# 09 Business Model Map

사업화 아이디어 및 비즈니스 모델 허브.

---

## 핵심 태그

`#area/business_model` `#type/idea` `#type/strategy`

---

## 사업화 가능 아이디어

```dataview
TABLE category AS "분류", summary AS "요약", business_value AS "사업 가치", automation_value AS "자동화 가치", next_action AS "다음 행동"
FROM #area/business_model
WHERE business_value = "high" OR automation_value = "high"
SORT file.mtime DESC
```

## 전체 사업 모델 목록

```dataview
TABLE summary AS "요약", status AS "상태", priority AS "우선순위"
FROM #area/business_model
SORT priority ASC, file.mtime DESC
```
