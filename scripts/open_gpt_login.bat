@echo off
chcp 65001 > nul
set PROFILE="G:\내 드라이브\obsidian-agent-brain-system\.gpt_collector_profile"
"C:\Program Files\Google\Chrome\Application\chrome.exe" --user-data-dir=%PROFILE% https://chatgpt.com/
