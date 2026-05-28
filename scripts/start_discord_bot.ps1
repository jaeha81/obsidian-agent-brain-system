#!/usr/bin/env pwsh
# Discord Bot 시작 스크립트 (백그라운드 실행)

param(
    [switch]$Wait = $false
)

$ROOT = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$BOT_SCRIPT = Join-Path $ROOT "scripts" "discord_bot.py"
$LOG_FILE = Join-Path $ROOT ".logs" "discord_bot_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

# 로그 디렉토리 생성
$LOG_DIR = Split-Path -Parent $LOG_FILE
if (-not (Test-Path $LOG_DIR)) {
    New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null
}

Write-Host "🚀 Discord Bot 시작 중..." -ForegroundColor Green
Write-Host "로그: $LOG_FILE" -ForegroundColor Cyan

# Python 백그라운드 실행
$process = Start-Process `
    -FilePath python `
    -ArgumentList $BOT_SCRIPT `
    -WorkingDirectory $ROOT `
    -RedirectStandardOutput $LOG_FILE `
    -RedirectStandardError $LOG_FILE `
    -PassThru `
    -WindowStyle Hidden

Write-Host "✅ Bot PID: $($process.Id)" -ForegroundColor Green

if ($Wait) {
    Write-Host "대기 중... (Ctrl+C로 중단)" -ForegroundColor Yellow
    $process.WaitForExit()
}
else {
    Start-Sleep -Seconds 2
    if ($process.HasExited) {
        Write-Host "❌ Bot 시작 실패!" -ForegroundColor Red
        Get-Content $LOG_FILE -Tail 20 | Write-Host -ForegroundColor Red
    }
    else {
        Write-Host "✨ Bot이 백그라운드에서 실행 중입니다" -ForegroundColor Green
        Write-Host "로그 확인: Get-Content '$LOG_FILE' -Wait" -ForegroundColor Cyan
    }
}
