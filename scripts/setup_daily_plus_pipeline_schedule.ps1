# setup_daily_plus_pipeline_schedule.ps1
# Windows Task Scheduler에 Daily Plus 전체 파이프라인 등록
# 매일 08:00 실행: 수집 -> GPT 세션 -> 대시보드 -> git push

$ErrorActionPreference = "Stop"

$taskName = "BuckyDailyPlusPipeline"
$pipelineScript = Join-Path $PSScriptRoot "run_daily_plus_pipeline.ps1"
$repoRoot = Split-Path $PSScriptRoot -Parent
$powershellExe = "powershell.exe"

if (-not (Test-Path -LiteralPath $pipelineScript)) {
    throw "Pipeline script not found: $pipelineScript"
}

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

# 기존 개별 태스크 비활성화 (충돌 방지)
@("BuckyDailyPlus", "BuckyDailyPlusDashboard") | ForEach-Object {
    $existing = Get-ScheduledTask -TaskName $_ -ErrorAction SilentlyContinue
    if ($existing) {
        Disable-ScheduledTask -TaskName $_ -ErrorAction SilentlyContinue | Out-Null
        Write-Host "[INFO] Disabled conflicting task: $_"
    }
}

$action = New-ScheduledTaskAction `
    -Execute $powershellExe `
    -Argument "-NonInteractive -ExecutionPolicy Bypass -File `"$pipelineScript`"" `
    -WorkingDirectory $repoRoot

$trigger = New-ScheduledTaskTrigger -Daily -At "08:00"

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Bucky: Daily Plus 전체 파이프라인 (Pulse 수집 + GPT 세션 + 대시보드 + git push)"

Write-Host ""
Write-Host "[OK] Registered: $taskName (daily 08:00)"
Write-Host "[INFO] Script: $pipelineScript"
Write-Host ""
Write-Host "수동 실행:"
Write-Host "  powershell -ExecutionPolicy Bypass -File `"$pipelineScript`""
Write-Host ""
Write-Host "git push 없이 테스트:"
Write-Host "  powershell -ExecutionPolicy Bypass -File `"$pipelineScript`" -SkipGitPush"
Write-Host ""
Write-Host "GPT 세션 수집 건너뛰기:"
Write-Host "  powershell -ExecutionPolicy Bypass -File `"$pipelineScript`" -SkipGptSession"
