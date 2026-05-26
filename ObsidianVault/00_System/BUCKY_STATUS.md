---
type: bucky-status
updated: 2026-05-27
pc: 집 PC
hostname: P0517A-22H2T8
username: user1
agent: 버키
runtime: claude_cli
---

# 버키 Status

| Item | Value |
|---|---|
| PC | 집 PC |
| Hostname | P0517A-22H2T8 |
| Username | user1 |
| Root | G:\내 드라이브\obsidian-agent-brain-system |
| Vault | G:\내 드라이브\obsidian-agent-brain-system |
| Agent Vault | G:\내 드라이브\obsidian-agent-brain-system\ObsidianVault |
| Auto Start | on |
| Chat | open |

## Runtime

| Script | Running |
|---|---|
| scripts/raw_import_watcher.py | yes |
| scripts/codex_review_runner.py | yes |
| scripts/agent_dispatcher.py | yes |

## Last Start Result

- started: none
- already_running: scripts/raw_import_watcher.py, scripts/codex_review_runner.py, scripts/agent_dispatcher.py
- missing: none

## Active Projects

| Project | Status | URL |
|---|---|---|
| 스나이퍼 구매대행 플랫폼 | MVP v0.1 배포 완료 | https://sniper-buying-dashboard.vercel.app/ |
| Wishket 자동화 에이전트 | Phase 3 테스트 통과 (23/23) | — |

## System Upgrades (2026-05-27)

- **장기 기억**: 봇 재시작 후에도 대화 기억, 중요 사실 자동 추출 → BUCKY_CONTEXT 기록
- **4채널 체계**: #jh-chat / #jh-tasks / #jh-status / #jh-results
  - `#jh-tasks`: Claude 불경유 즉시 배정 (<1초)
  - `#jh-results`: 완료 시 @멘션 자동 알림
- **응답 속도**: "🤔 생각 중..." 즉시 표시 + RAG 스킵 휴리스틱

## Rules

- Obsidian desktop loads the bucky-agent plugin.
- Plugin detects local PC and starts Bucky scripts when autoStart is on.
- Duplicate process check prevents launching the same script twice.
- Bucky Chat calls the Claude CLI subscription route through scripts/bucky_chat_once.py.
- Long-term memory: key facts auto-extracted from conversations and written to BUCKY_CONTEXT.