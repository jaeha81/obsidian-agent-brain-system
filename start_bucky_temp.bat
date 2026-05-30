@echo off
cd /d "G:\? ????\obsidian-agent-brain-system"
python -X utf8 scripts\bucky_bot_supervisor.py > "logs\discord_bot.log" 2> "logs\discord_bot_err.log"
