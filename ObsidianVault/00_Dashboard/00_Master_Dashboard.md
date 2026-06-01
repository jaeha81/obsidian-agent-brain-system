---
type: system-doc
status: active
created: 2026-05-31
owner: Bucky
tags:
  - #status/active
---

# 00 Master Dashboard

Obsidian Agent Brain System의 중앙 지식 지도. 모든 영역의 허브 노트.

---

## 핵심 영역 지도

- [[01_GPT_Feedback_Map]] — GPT/오늘의 플러스 피드백 기록
- [[02_AI_Automation_Map]] — AI 자동화 시스템
- [[03_Make_Workflows_Map]] — Make.com 워크플로우
- [[04_Obsidian_Brain_Map]] — 지식관리 시스템 구조
- [[05_Interior_Business_Map]] — 인테리어 업무 관리
- [[06_Client_Vendor_Map]] — 클라이언트/협력사
- [[07_Monetization_Map]] — 수익화 전략
- [[08_Investment_Map]] — 투자 메모
- [[09_Business_Model_Map]] — 사업화 아이디어
- [[10_Action_Dashboard]] — 오늘 실행할 일
- [[11_Keyword_Index]] — 전체 키워드 인덱스
- [[99_Archive_Map]] — 아카이브

---

## 오늘 확인할 항목

```dataview
TABLE category AS "분류", summary AS "요약", priority AS "우선순위", next_action AS "다음 행동"
FROM ""
WHERE (status = "inbox" OR status = "review_needed") AND summary
  AND !contains(file.path, "10_AgentBus/inbox") AND !contains(file.path, "10_AgentBus/outbox")
  AND !contains(file.path, "10_AgentBus/completed") AND !contains(file.path, "10_AgentBus/failed")
  AND !contains(file.path, "Inbox/DiscordCaptures")
SORT file.mtime DESC
LIMIT 20
```

## P1 우선순위 실행 목록

```dataview
TABLE category AS "분류", summary AS "요약", next_action AS "다음 행동", review_date AS "검토일"
FROM ""
WHERE priority = "p1" AND summary
SORT file.mtime DESC
```

---

## 시스템 연결

- [[00_System/ROUTING_RULES]] — 에이전트 라우팅 규칙
- [[00_System/BUCKY_STATUS]] — Bucky 현재 상태
- [[00_System/TAG_STANDARD]] — 태그 체계
- [[00_System/YAML_STANDARD]] — YAML 스키마
