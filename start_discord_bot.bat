@echo off
setlocal
cd /d "%~dp0"

echo [Bot] Discord Bucky Bot supervisor
echo [Bot] Root: %~dp0
echo [Bot] Logs: discord_bot.log / discord_bot.err
echo [Bot] Restart signal: ObsidianVault\10_AgentBus\signals\bot_restart.signal
echo [Bot] Stop: press Ctrl+C in this window
echo.

python scripts\bucky_bot_supervisor.py
set EXIT_CODE=%ERRORLEVEL%

echo.
echo [Bot] Supervisor exited with code %EXIT_CODE%.
exit /b %EXIT_CODE%
