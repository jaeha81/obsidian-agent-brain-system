---
title: 옵시디언과 에이전트 연결 다리
date: 2026-05-30
source: daily-plus/2026-05-30.md (Card 8)
priority: P1
category: knowledge
status: distilled
tags:
  - obsidian
  - mcp
  - agent
  - claude
  - bridge
  - daily-plus
  - knowledge
---

# 옵시디언과 에이전트 연결 다리

> ChatGPT Pulse 2026-05-30 Card 8 증류 (P1 · knowledge-candidate)

## 목적

Obsidian 볼트를 MCP(Model Context Protocol)로 에이전트(Claude Code/CLI)에 연결하면 질의·작성·패치가 가능한 라이브 작업공간이 된다. 보안은 읽기+제한적 append 가드와 폴더 정책으로 관리한다.

## MCP 연결 방식

```json
// .claude/settings.json 또는 mcp.json
{
  "mcpServers": {
    "obsidian-vault": {
      "command": "node",
      "args": ["path/to/obsidian-mcp-server/index.js"],
      "env": {
        "VAULT_PATH": "G:/내 드라이브/obsidian-agent-brain-system/ObsidianVault",
        "ACCESS_POLICY": "read_and_append"
      }
    }
  }
}
```

## 보안 설정

```yaml
vault_access_policy:
  default: read_only
  allowed_write_paths:
    - "03_Knowledge/"   # 지식 노트 생성/수정
    - "00_System/HANDOFF_LOG.md"  # 핸드오프 로그 append
  forbidden_paths:
    - "00_System/ROUTING_RULES.md"  # 보호 파일
    - "03_Projects/agents/bucky.md" # 보호 파일
  write_modes:
    "03_Knowledge/": "create_or_update"
    "00_System/HANDOFF_LOG.md": "append_only"
  require_sha256_verify: true   # 읽기 시 SHA-256 검증
  max_file_size_kb: 500         # 단일 파일 최대 크기
```

## 폴더 정책 예시

| 폴더 | 에이전트 접근 | 허용 액션 |
|------|--------------|----------|
| 00_System/ | 읽기 전용 (일부 append) | read, append(HANDOFF_LOG만) |
| 03_Knowledge/ | 읽기 + 쓰기 | read, create, update |
| 03_Projects/ | 읽기 전용 | read |
| 10_AgentBus/ | 읽기 전용 | read |

## 활용 패턴

### 1. 지식 질의
```
에이전트 → MCP read → 볼트 노트 검색 → 컨텍스트 주입
```

### 2. 노트 자동 생성
```
에이전트 → MCP write → 03_Knowledge/ 새 파일 생성
```

### 3. 핸드오프 기록
```
에이전트 → MCP append → HANDOFF_LOG.md 상태 기록
```

### 4. 변경 감지 루프
```
에이전트 → MCP read sha256 → 변경 감지 → 파이프라인 트리거
```

## 관련 컨텍스트

- [[2026-05-30-dp-obsidian-yaml-standard]] — YAML 표준 및 SHA-256 검증
- [[2026-05-31-dp-folder-permission-graph]] — 폴더 권한 결정 매트릭스
- [[2026-05-31-dp-yaml-graph-color-acl]] — 그래프 색상 ACL
