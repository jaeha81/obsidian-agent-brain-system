---
type: bucky-status
updated: 2026-05-28T19:00:00.000Z
pc: 집 PC
hostname: DESKTOP-6F8H500
username: 설계4
agent: 버키
runtime: claude_cli
---

# 버키 Status

| Item | Value |
|---|---|
| PC | 집 PC |
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
| scripts/bucky_bot_supervisor.py | yes (PID 4892) |
| scripts/discord_bot.py | yes (PID 36756) |
| scripts/agent_dispatcher.py | no |

## Last Start Result

- started: bucky_bot_supervisor.py → discord_bot.py
- BOT_ALLOWED_HOSTNAME: DESKTOP-6F8H500 (크로스 머신 이중 실행 방지)
- Thinking 메시지 잔여 정리: _active_thinking_msgs 활성

## Rules

- Obsidian desktop loads the bucky-agent plugin.
- Plugin detects local PC and starts Bucky scripts when autoStart is on.
- Duplicate process check prevents launching the same script twice.
- Bucky Chat calls the Claude CLI subscription route through scripts/bucky_chat_once.py.
- BOT_ALLOWED_HOSTNAME enforces single-machine bot execution across Google Drive shared machines.
