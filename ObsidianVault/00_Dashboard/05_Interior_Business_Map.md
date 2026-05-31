---
type: system-doc
status: active
created: 2026-05-31
owner: Bucky
tags:
  - #status/active
---

# 05 Interior Business Map

인테리어 업무 관리 허브. 견적, 시공, 현장관리 통합.

---

## 핵심 태그

`#area/interior_design` `#area/construction` `#area/field_management`

---

## 인테리어 업무 대시보드

```dataview
TABLE summary AS "요약", source AS "출처", status AS "상태", next_action AS "다음 행동"
FROM #area/interior_design OR #area/construction OR #area/field_management
SORT file.mtime DESC
```

## 현장관리 노트

```dataview
TABLE summary AS "요약", status AS "상태", next_action AS "다음 행동"
FROM #area/field_management
SORT file.mtime DESC
```
