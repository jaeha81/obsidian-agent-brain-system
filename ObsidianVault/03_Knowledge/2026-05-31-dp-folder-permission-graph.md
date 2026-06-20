---
title: 폴더 권한과 그래프 판단표
date: 2026-05-31
source: daily-plus/2026-05-31.md (Card 2)
priority: P1
category: knowledge
status: distilled
tags:
- acl
- vault
- permissions
- agent
- security
- daily-plus
- knowledge
- source/today_plus
- type/reference
graph_cluster: daily-practice
---

# 폴더 권한과 그래프 판단표

> ChatGPT Pulse 2026-05-31 Card 2 증류 (P1 · knowledge-candidate)

## 목적

에이전트가 지식 저장소에 무엇을 할 수 있는지를 딱 잘라 정하는 결정 매트릭스. 누가 어디에 어떤 권한으로 접근하는지 자동 점검한다.

## 역할별 폴더 권한 매트릭스

| 폴더 | 사람(JH) | Bucky | Claude Code | Codex | 외부 에이전트 |
|------|---------|-------|------------|-------|--------------|
| 00_System/ | RW | R | R | R | - |
| 00_System/HANDOFF_LOG.md | RW | RW(append) | RW(append) | R | - |
| 00_System/ROUTING_RULES.md | RW | R | R | R | - |
| 03_Knowledge/ | RW | RW | RW | R | - |
| 03_Projects/ | RW | RW | R | R | - |
| 03_Projects/agents/ | RW | R | R | R | - |
| 10_AgentBus/ | RW | RW | R | R | - |

범례: R=읽기, W=쓰기, RW=읽기+쓰기, -=접근 없음

## 에이전트별 허용 액션

```yaml
bucky:
  allowed:
    - read_all
    - write: ["03_Knowledge/", "10_AgentBus/"]
    - append: ["00_System/HANDOFF_LOG.md"]
  forbidden:
    - write: ["00_System/ROUTING_RULES.md", "03_Projects/agents/bucky.md"]
    - delete: ["**"]   # 삭제 전면 금지

claude_code:
  allowed:
    - read_all
    - write: ["03_Knowledge/"]
    - append: ["00_System/HANDOFF_LOG.md"]
  forbidden:
    - write: ["00_System/", "03_Projects/agents/"]
    - delete: ["**"]

codex:
  allowed:
    - read_all
  forbidden:
    - write: ["**"]
    - delete: ["**"]
```

## 위반 감지 방법

```python
FORBIDDEN_WRITE = [
    "00_System/ROUTING_RULES.md",
    "03_Projects/agents/bucky.md",
    "03_Projects/agents/",
]

def check_write_permission(agent: str, path: str) -> bool:
    for forbidden in FORBIDDEN_WRITE:
        if path.startswith(forbidden):
            log_violation(agent, path, action="write")
            return False
    return True
```

감사 로그는 `00_System/acl_violations.jsonl`에 append-only 기록.

## 관련 컨텍스트

- [[2026-05-30-dp-obsidian-agent-bridge]] — MCP 연결 방식
- [[2026-05-31-dp-yaml-graph-color-acl]] — 그래프 색상 ACL 연동
