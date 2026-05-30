---
type: bucky-status
updated: 2026-05-30T21:00:00.000Z
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

- started: scripts/raw_import_watcher.py, scripts/agent_dispatcher.py
- already_running: scripts/codex_review_runner.py
- missing: none

## AgentBus Phase 1 Gate 완료 현황 (2026-05-30)

| Gate | 내용 | 상태 |
|------|------|------|
| 1 | registry repair 40 | ✅ 완료 |
| 2 | cleanup 564 | ✅ 완료 |
| 3 | external blockers 9 | ✅ 코드 완료 / ⏳ 빌링 사용자 액션 |
| 4 | Sniper v0.2 | ✅ 완료 |
| 5 | Discord voice live | ✅ 완료 |
| 6 | Hermes cleanup | ✅ 완료 |
| 7 | T013/T020 | ✅ 완료 |

빌링 잔여: Anthropic 크레딧 충전(console.anthropic.com), OpenAI quota 증가

## Rules

- Obsidian desktop loads the bucky-agent plugin.
- Plugin detects local PC and starts Bucky scripts when autoStart is on.
- Duplicate process check prevents launching the same script twice.
- Bucky Chat calls the Claude CLI subscription route through scripts/bucky_chat_once.py.