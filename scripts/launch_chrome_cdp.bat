@echo off
chcp 65001 > nul
echo Chrome을 CDP 디버그 모드로 시작합니다...
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --remote-allow-origins=* https://chatgpt.com/
