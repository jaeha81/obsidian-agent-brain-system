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

## 핵심 노트

- [[05_인테리어_견적시스템]] — 14단계 견적 흐름 / JH-견적시스템 아키텍처
- [[2026-05-27-spaceplanner---interior-design-platform]] — SpacePlanner 3D 플랫폼 리서치
- [[2026-05-27-spaceplanner---interior-design-platform (1)]] — SpacePlanner 리서치 사본

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
