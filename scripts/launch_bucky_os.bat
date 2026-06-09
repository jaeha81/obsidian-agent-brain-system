@echo off
:: Bucky Agent OS Launcher
:: Flask 서버 시작 + Chrome에서 자동 로그인

set ROOT=%~dp0..
set PYTHON=python

:: 1. 포트 8765 사용 중인지 확인
netstat -ano | findstr /R ":8765 " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    echo [Bucky OS] Flask 서버 시작 중...
    start /B "" %PYTHON% -X utf8 "%ROOT%\scripts\bucky_chat_server.py"
    :: 서버 준비 대기
    timeout /t 3 /nobreak >nul
) else (
    echo [Bucky OS] 서버 이미 실행 중.
)

:: 2. Chrome에서 /launch 엔드포인트 열기 (자동 쿠키 설정 후 bucky-os.html 리다이렉트)
start "" "chrome.exe" "http://localhost:8765/launch"
