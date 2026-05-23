---
type: bucky-status
updated: 2026-05-23T09:03:51.704Z
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
| Auto Start | on |

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
- Agent runtime uses the existing Claude CLI subscription route.