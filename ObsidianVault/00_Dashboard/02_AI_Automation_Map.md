---
type: system-doc
status: active
created: 2026-05-31
owner: Bucky
tags:
  - #status/active
---

# 02 AI Automation Map

AI 자동화 시스템 허브. 구현 중/완료/아이디어 전체 추적.

---

## 핵심 태그

`#area/ai_automation` `#area/make_com`

---

## 핵심 노트

- [[00_overview]] — JH 메모리 전체 개요
- [[07_jh_brain]] — JH Brain 에이전트 아키텍처
- [[06_jh_harness]] — JH Harness 시스템
- [[10_AgentBus/index]] — AgentBus 인덱스

---

## AI 자동화 대시보드

```dataview
TABLE summary AS "요약", keywords AS "키워드", automation_value AS "자동화 가치", next_action AS "다음 행동"
FROM #area/ai_automation
SORT file.mtime DESC
```

## Make.com 워크플로우

```dataview
TABLE summary AS "요약", keywords AS "키워드", status AS "상태", next_action AS "다음 행동"
FROM #area/make_com
SORT priority ASC, file.mtime DESC
```

## 자동화 아이디어 (보류 포함)

```dataview
TABLE summary AS "요약", status AS "상태", automation_value AS "자동화 가치"
FROM #area/ai_automation OR #area/make_com
WHERE status = "hold" OR status = "inbox"
SORT file.mtime DESC
```
