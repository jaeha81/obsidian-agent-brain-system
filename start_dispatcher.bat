@echo off
:: Agent Dispatcher 시작 스크립트
:: .env에 ANTHROPIC_API_KEY 설정 후 실행

cd /d "%~dp0"
echo [Dispatcher] Starting Agent Dispatcher...
echo [Dispatcher] Vault: ObsidianVault\10_AgentBus\inbox\
echo [Dispatcher] CTRL+C to stop
echo.
python scripts\agent_dispatcher.py
pause
