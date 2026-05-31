---
type: system-doc
status: active
created: 2026-05-31
owner: Bucky
tags:
  - #status/active
---

# 07 Monetization Map

콘텐츠 수익화 / 웹 광고 수익 허브.

---

## 핵심 태그

`#area/content_monetization` `#area/web_revenue`

---

## 수익화 대시보드

```dataview
TABLE summary AS "요약", keywords AS "키워드", business_value AS "사업 가치", next_action AS "다음 행동"
FROM #area/content_monetization OR #area/web_revenue
SORT business_value DESC, file.mtime DESC
```

## P1 수익화 항목

```dataview
TABLE summary AS "요약", next_action AS "다음 행동"
FROM #area/content_monetization OR #area/web_revenue
WHERE priority = "p1"
SORT file.mtime DESC
```
