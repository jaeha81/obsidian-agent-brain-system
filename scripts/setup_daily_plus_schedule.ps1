# setup_daily_plus_schedule.ps1
# Windows Task Scheduler에 매일 오전 8시 자동 수집 등록

$taskName   = "BuckyDailyPlus"
$scriptPath = "G:\내 드라이브\obsidian-agent-brain-system\scripts\chatgpt_daily_collector.py"
$workDir    = "G:\내 드라이브\obsidian-agent-brain-system\scripts"

# 기존 작업 삭제 (재등록)
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction `
    -Execute "python" `
    -Argument "`"$scriptPath`" --collect" `
    -WorkingDirectory $workDir

# 매일 오전 8:00
$trigger = New-ScheduledTaskTrigger -Daily -At "08:00"

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Bucky: ChatGPT 오늘의 플러스 자동 수집 → ObsidianVault 04_Wiki/daily-plus/" `
    -RunLevel Highest

Write-Host "[OK] 스케줄 등록 완료: 매일 오전 08:00 자동 실행"
Write-Host "[INFO] 작업명: $taskName"
Write-Host ""
Write-Host "=== 사용법 ==="
Write-Host "1. 최초 로그인 (1회만):"
Write-Host "   python `"$scriptPath`" --login"
Write-Host ""
Write-Host "2. 수동 즉시 수집:"
Write-Host "   python `"$scriptPath`" --collect"
Write-Host ""
Write-Host "3. Task Scheduler에서 즉시 실행:"
Write-Host "   Start-ScheduledTask -TaskName $taskName"
