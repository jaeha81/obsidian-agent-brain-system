---
type: bucky-status
<<<<<<< Updated upstream
updated: 2026-05-25T02:00:53.513Z
=======
updated: 2026-05-25T01:59:54.368Z
>>>>>>> Stashed changes
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

## Rules

- Obsidian desktop loads the bucky-agent plugin.
- Plugin detects local PC and starts Bucky scripts when autoStart is on.
- Duplicate process check prevents launching the same script twice.
- Bucky Chat calls the Claude CLI subscription route through scripts/bucky_chat_once.py.