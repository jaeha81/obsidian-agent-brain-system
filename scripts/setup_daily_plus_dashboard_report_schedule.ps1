# setup_daily_plus_dashboard_report_schedule.ps1
# Register BuckyDailyPlusDashboard in Windows Task Scheduler.
# This runs the generated Daily Plus dashboard and morning report at 09:00 KST.

$ErrorActionPreference = "Stop"

$taskName = "BuckyDailyPlusDashboard"
$scriptPath = Join-Path $PSScriptRoot "daily_plus_morning_report.py"
$repoRoot = Split-Path $PSScriptRoot -Parent
$pythonExe = (Get-Command python).Source

if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Morning report script not found: $scriptPath"
}

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction `
    -Execute $pythonExe `
    -Argument "`"$scriptPath`"" `
    -WorkingDirectory $repoRoot

$trigger = New-ScheduledTaskTrigger -Daily -At "09:00"

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Bucky: generate Daily Plus dashboard and 09:00 morning report for user review"

Write-Host "[OK] Registered: $taskName (daily 09:00)"
Write-Host "[INFO] Python: $pythonExe"
Write-Host "[INFO] Script: $scriptPath"
Write-Host ""
Write-Host "Manual report:"
Write-Host "  `"$pythonExe`" `"$scriptPath`""
