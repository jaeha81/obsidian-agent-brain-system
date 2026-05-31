---
type: bucky-status
updated: 2026-05-31T23:29:01.911Z
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
| scripts/raw_import_watcher.py | no |
| scripts/codex_review_runner.py | no |
| scripts/agent_dispatcher.py | no |

## Last Start Result

- started: none
- already_running: none
- missing: none

## Rules

- Obsidian desktop loads the bucky-agent plugin.
- Plugin detects local PC and starts Bucky scripts when autoStart is on.
- Duplicate process check prevents launching the same script twice.
- Bucky Chat calls the Claude CLI subscription route through scripts/bucky_chat_once.py.