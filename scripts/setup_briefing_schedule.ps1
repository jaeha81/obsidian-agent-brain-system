# Bucky Daily Briefing — Windows Task Scheduler 등록
# 매일 오전 8:00 자동 브리핑 생성 (Obsidian 저장만, Discord 전송은 봇 명령으로)
#
# 실행: powershell -ExecutionPolicy Bypass -File setup_briefing_schedule.ps1

$taskName  = "BuckyDailyBriefing"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir   = Split-Path -Parent $scriptDir
$pythonExe = "python"
$scriptPath = Join-Path $scriptDir "bucky_briefing.py"
$logPath    = Join-Path $rootDir "logs\briefing.log"

# 로그 폴더 생성
$logsDir = Join-Path $rootDir "logs"
if (-not (Test-Path $logsDir)) { New-Item -ItemType Directory -Path $logsDir | Out-Null }

$action  = New-ScheduledTaskAction `
    -Execute $pythonExe `
    -Argument "`"$scriptPath`" >> `"$logPath`" 2>&1" `
    -WorkingDirectory $rootDir

$trigger = New-ScheduledTaskTrigger -Daily -At "08:00AM"

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

try {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Description "Bucky AI/기술 일일 브리핑 자동 생성 (매일 08:00)" `
        -RunLevel Highest
    Write-Host "[OK] 스케줄 등록 완료: '$taskName' — 매일 오전 8:00"
    Write-Host "     스크립트: $scriptPath"
    Write-Host "     로그: $logPath"
} catch {
    Write-Host "[ERROR] 스케줄 등록 실패: $_"
}
