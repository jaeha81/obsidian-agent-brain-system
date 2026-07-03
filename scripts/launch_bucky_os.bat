@echo off
chcp 65001 >nul 2>&1

set ROOT=%~dp0..
set PYTHON=C:\Python314\python.exe
set CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe

netstat -ano | findstr /R ":8765 " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    echo [Bucky OS] Starting Flask server...
    start /B "" "%PYTHON%" -X utf8 "%ROOT%\scripts\bucky_chat_server.py"
    timeout /t 3 /nobreak >nul
) else (
    echo [Bucky OS] Server already running.
)

if exist "%CHROME%" (
    start "" "%CHROME%" "http://localhost:8765/launch"
) else (
    start "" "http://localhost:8765/launch"
)
