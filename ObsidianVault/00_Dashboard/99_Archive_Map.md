---
type: system-doc
status: active
created: 2026-05-31
owner: Bucky
tags:
  - #status/active
---

# 99 Archive Map

아카이브된 노트 전체 조회.

---

## 핵심 태그

`#status/archive` `#status/hold`

---

## 아카이브 목록

```dataview
TABLE category AS "분류", summary AS "요약", file.mtime AS "최종 수정"
FROM ""
WHERE status = "archive"
SORT file.mtime DESC
LIMIT 50
```

## 보류 항목

```dataview
TABLE summary AS "요약", next_action AS "다음 행동"
FROM ""
WHERE status = "hold"
SORT file.mtime DESC
```
