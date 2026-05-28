---
type: bucky-status
updated: 2026-05-28T09:45:36.637Z
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
| Vault | G:\내 드라이브\obsidian-agent-brain-system |
| Agent Vault | G:\내 드라이브\obsidian-agent-brain-system\ObsidianVault |
| Auto Start | on |
| Chat | open |

## Runtime

| Script | Running |
|---|---|
| scripts/raw_import_watcher.py | no |
| scripts/codex_review_runner.py | no |
| scripts/agent_dispatcher.py | no |

## Last Start Result

- started: scripts/raw_import_watcher.py, scripts/codex_review_runner.py, scripts/agent_dispatcher.py
- already_running: none
- missing: none

## Rules

- Obsidian desktop loads the bucky-agent plugin.
- Plugin detects local PC and starts Bucky scripts when autoStart is on.
- Duplicate process check prevents launching the same script twice.
- Bucky Chat calls the Claude CLI subscription route through scripts/bucky_chat_once.py.