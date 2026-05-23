@echo off
:: Agent Dispatcher + RAW Import Watcher start script
:: Requires configured local agent CLI.

cd /d "%~dp0"
echo [System] Starting Obsidian Agent Brain System...
echo [System] AgentBus Inbox : ObsidianVault\10_AgentBus\inbox\
echo [System] RAW Import     : RAW_IMPORT\
echo [System] Codex Review   : ObsidianVault\10_AgentBus\outbox\Hermes\
echo [System] Harness Router : ObsidianVault\05_Frameworks\Harness\
echo [System] CTRL+C to stop dispatcher; close watcher windows to stop them
echo.

:: RAW Import Watcher - 별도 창에서 실행
start "RAW Import Watcher" cmd /k "cd /d ""%~dp0"" && python scripts\raw_import_watcher.py"

:: Codex Review Runner - 별도 창에서 실행
start "Codex Review Runner" cmd /k "cd /d ""%~dp0"" && python scripts\codex_review_runner.py"

:: Agent Dispatcher - 현재 창에서 실행
echo [Dispatcher] Starting Agent Dispatcher...
python scripts\agent_dispatcher.py
pause
