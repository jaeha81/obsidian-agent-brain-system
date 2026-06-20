---
title: YAML 그래프 색상과 안전 ACL
date: 2026-05-31
source: daily-plus/2026-05-31.md (Card 3)
priority: P1
category: knowledge
status: distilled
tags:
- yaml
- obsidian-graph
- color
- acl
- visualization
- daily-plus
- knowledge
- source/today_plus
- type/reference
graph_cluster: daily-practice
---

# YAML 그래프 색상과 안전 ACL

> ChatGPT Pulse 2026-05-31 Card 3 증류 (P1 · knowledge-candidate)

## 목적

frontmatter 필드를 Obsidian 그래프 시각화의 그룹/색상 레이어로 매핑하는 방법과 안전한 자동화 범위 관리.

## frontmatter 색상 그룹 필드

```yaml
---
# 그래프 색상 그룹 필드 (선택)
graph_group: knowledge    # knowledge | system | project | task | agent
graph_color: "#4CAF50"    # HEX 색상 코드 (선택, 없으면 그룹 기본색 사용)
---
```

## 그룹별 기본 색상 매핑

| graph_group | 색상 HEX | Obsidian 그래프 의미 |
|-------------|---------|---------------------|
| knowledge | #4CAF50 | 녹색 — 지식/학습 노트 |
| system | #2196F3 | 파란색 — 시스템/설정 |
| project | #FF9800 | 주황색 — 프로젝트/작업 |
| task | #F44336 | 빨간색 — 긴급 태스크 |
| agent | #9C27B0 | 보라색 — 에이전트 설정 |

## 그래프 필터 설정

Obsidian Graph View 설정에서 `graph_group` 필드를 기준으로 그룹 필터를 설정한다.

```json
// Obsidian Graph 그룹 규칙 (JSON 형식)
[
  { "query": "\"graph_group: knowledge\"", "color": "#4CAF50" },
  { "query": "\"graph_group: system\"",    "color": "#2196F3" },
  { "query": "\"graph_group: project\"",   "color": "#FF9800" },
  { "query": "\"graph_group: task\"",      "color": "#F44336" },
  { "query": "\"graph_group: agent\"",     "color": "#9C27B0" },
  { "query": "tag:#rflag-true",            "color": "#FF0000" }
]
```

## ACL 정책 연동

`rflag: true` 노트는 그래프에서 빨간색으로 강조 표시되며, 에이전트 자동 수정 범위에서 제외된다.

```yaml
acl_policy:
  auto_edit_allowed:
    graph_groups: [knowledge, task]
    rflag: false        # rflag=true 노트는 자동 수정 금지
  read_only:
    graph_groups: [system, agent]
  human_review_required:
    rflag: true
    graph_groups: [system, agent]
```

## 활용 패턴

- 에이전트가 노트 생성 시 `graph_group`과 `cat` 필드를 함께 설정
- 그래프에서 클러스터 색상으로 지식 구조 시각화
- `rflag: true` 노트가 붉게 표시되어 검토 우선순위 파악

## 관련 컨텍스트

- [[2026-05-30-dp-obsidian-yaml-standard]] — YAML 표준 및 rflag 필드
- [[2026-05-31-dp-folder-permission-graph]] — 폴더 권한 매트릭스
