---
title: 오늘 운영 스냅샷과 원클릭 액션
date: 2026-05-31
source: daily-plus/2026-05-31.md (Card 1)
priority: P2
category: knowledge
status: distilled
tags:
- ops
- snapshot
- dashboard
- manifest
- bucky
- daily-plus
- knowledge
- source/today_plus
- type/reference
graph_cluster: daily-practice
---

# 오늘 운영 스냅샷과 원클릭 액션

> ChatGPT Pulse 2026-05-31 Card 1 증류 (P2 · knowledge-candidate)

## 목적

아침 운영 스냅샷을 한 줄로 붙여 넣어 즉시 쓰는 포맷. GitHub/리드/최우선 작업을 "돈 되는 것 먼저" 관점으로 압축. 원클릭 액션 포함 JSON 포맷.

## dailyops manifest 구조

```json
{
  "schema": "dailyops_v1",
  "date": "2026-05-31",
  "generated_at": "2026-05-31T08:00:00Z",
  "money_first": {
    "top_revenue_task": "업셀 전환율 개선 — CVR 4% → 8%",
    "estimated_impact_krw": 500000,
    "deadline": "2026-06-07"
  },
  "github": {
    "open_prs": 2,
    "failing_checks": 1,
    "review_requested": 1
  },
  "leads": {
    "hot": 3,
    "warm": 7,
    "cold": 12,
    "follow_up_today": ["lead-A", "lead-B"]
  },
  "priority_tasks": [
    { "id": "T001", "title": "업셀 A/B 테스트 결과 분석", "p": "P0" },
    { "id": "T002", "title": "Stripe 웹훅 재시도 로직", "p": "P1" }
  ],
  "actions": []
}
```

## 원클릭 액션 정의

```json
"actions": [
  {
    "id": "review-pr",
    "label": "PR 검토",
    "trigger": "/bucky review pr --repo obsidian-agent-brain-system",
    "type": "discord_command"
  },
  {
    "id": "run-upsell-check",
    "label": "업셀 게이트 점검",
    "trigger": "/bucky gate check upsell-launch",
    "type": "discord_command"
  },
  {
    "id": "morning-summary",
    "label": "아침 요약 생성",
    "trigger": "python scripts/morning_digest.py",
    "type": "local_script"
  }
]
```

## 우선순위 결정 방식

1. **P0** — 돈 직결 (수익, 결제, CVR 영향)
2. **P1** — 인프라·안정성 (배포, 장애 복구)
3. **P2** — 효율화 (자동화, 리팩토링)
4. **P3** — 탐색·실험 (PoC, 리서치)

매일 아침 P0 미해결 작업이 있으면 다른 항목 착수 금지.

## 관련 컨텍스트

- [[2026-05-30-dp-bucky-launch-gate]] — 런치 게이트 자동 점검
- [[2026-05-31-dp-decision-first-manifest]] — 결정 우선 압축 매니페스트
