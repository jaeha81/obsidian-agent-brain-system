---
type: system-doc
status: active
created: 2026-05-31
owner: Bucky
tags:
  - #status/active
---

# 03 Make Workflows Map

Make.com 자동화 워크플로우 전체 허브.

---

## 핵심 태그

`#area/make_com` `#type/workflow`

---

## Make.com 워크플로우 현황

```dataview
TABLE summary AS "요약", status AS "상태", next_action AS "다음 행동"
FROM #area/make_com
SORT priority ASC, file.mtime DESC
```

## 활성 워크플로우

```dataview
TABLE summary AS "요약", next_action AS "다음 행동"
FROM #area/make_com
WHERE status = "active"
SORT file.mtime DESC
```
