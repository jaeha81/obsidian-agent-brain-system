---
type: system-doc
status: active
created: 2026-05-31
owner: Bucky
tags:
  - #status/active
---

# 11 Keyword Index

Vault 전체 키워드 인덱스. Dataview로 자동 생성.

---

## 키워드별 노트 수

```dataview
TABLE rows.file.link AS "관련 노트", length(rows) AS "노트 수"
FROM ""
FLATTEN keywords AS keyword
GROUP BY keyword
SORT length(rows) DESC
LIMIT 50
```

## 태그별 노트 수

```dataview
TABLE length(rows) AS "노트 수"
FROM ""
FLATTEN file.tags AS tag
GROUP BY tag
SORT length(rows) DESC
LIMIT 30
```
