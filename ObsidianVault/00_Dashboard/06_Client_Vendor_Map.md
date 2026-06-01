---
type: system-doc
status: active
created: 2026-05-31
owner: Bucky
tags:
  - #status/active
---

# 06 Client Vendor Map

클라이언트 / 협력사 관리 허브.

---

## 핵심 태그

`#area/client_consulting` `#area/vendor_meeting` `#type/client` `#type/meeting` `#type/estimate`

---

## 핵심 노트

- [[11_client_projects]] — 클라이언트 납품 프로젝트 목록 (의료미용 D2C, EONID 포트폴리오 등)
- [[01_raw-memories-11_client_projects-md]] — Knowledge Bridge (클라이언트 프로젝트 연결)

---

## 클라이언트/견적 대시보드

```dataview
TABLE summary AS "요약", keywords AS "키워드", status AS "상태", next_action AS "다음 행동"
FROM #area/client_consulting
SORT file.mtime DESC
```

## 협력사/미팅 대시보드

```dataview
TABLE summary AS "요약", source AS "출처", status AS "상태", next_action AS "다음 행동"
FROM #area/vendor_meeting
SORT file.mtime DESC
```
