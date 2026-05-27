---
type: bucky-status
updated: 2026-05-27T04:39:59.688Z
pc: 사무실 PC
hostname: DESKTOP-6F8H500
username: 설계4
agent: 버키
runtime: claude_cli
---

# 버키 Status

| Item | Value |
|---|---|
| PC | 사무실 PC |
| Hostname | DESKTOP-6F8H500 |
| Username | 설계4 |
| Root | G:\내 드라이브\obsidian-agent-brain-system |
| Vault | G:\내 드라이브\obsidian-agent-brain-system\ObsidianVault |
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

## Rules

- Obsidian desktop loads the bucky-agent plugin.
- Plugin detects local PC and starts Bucky scripts when autoStart is on.
- Duplicate process check prevents launching the same script twice.
- Bucky Chat calls the Claude CLI subscription route through scripts/bucky_chat_once.py.

## Plugin Stack (2026-05-26)

**원칙**: Plugin으로 해결 가능한 기능은 직접 개발하지 않는다.

| 카테고리 | 플러그인 | 상태 |
|---------|---------|------|
| 자동화 | QuickAdd, Templater, Tasks, Shell Commands | ✅ 활성 |
| 데이터 | Dataview, Smart Connections | ✅ 활성 |
| UI | Meta Bind, Buttons, Kanban | ✅ 신규 |
| 검색 | Omnisearch | ✅ 활성 |
| 연동 | Local REST API, Git, Claudian | ✅ 활성 |

커스텀 필수: Discord 봇 · Claude API · 비동기 병렬 · 음성인식 · AI 패턴학습
상세: `00_System/plugin-stack/PLUGIN_STACK.md`