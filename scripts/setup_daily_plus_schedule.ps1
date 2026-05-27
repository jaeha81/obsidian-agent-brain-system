# setup_daily_plus_schedule.ps1
# Register BuckyDailyPlus in Windows Task Scheduler.
# This runs collection and Pulse Evolution Agent staging.

$ErrorActionPreference = "Stop"

$taskName = "BuckyDailyPlus"
$scriptPath = Join-Path $PSScriptRoot "chatgpt_daily_collector.py"
$repoRoot = Split-Path $PSScriptRoot -Parent
$pythonExe = (Get-Command python).Source

if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Collector not found: $scriptPath"
}

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction `
    -Execute $pythonExe `
    -Argument "`"$scriptPath`" --collect" `
    -WorkingDirectory $repoRoot

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
    -Description "Bucky: ChatGPT Pulse daily collection + evolution staging -> ObsidianVault/04_Wiki/daily-plus/ and 00_UPGRADE/pulse-evolution/" `
    -RunLevel Highest

Write-Host "[OK] Registered: $taskName (daily 08:00)"
Write-Host "[INFO] Python: $pythonExe"
Write-Host "[INFO] Script: $scriptPath"
Write-Host ""
Write-Host "Manual login:"
Write-Host "  `"$pythonExe`" `"$scriptPath`" --login"
Write-Host ""
Write-Host "Manual collect + evolve:"
Write-Host "  `"$pythonExe`" `"$scriptPath`" --collect"
Write-Host ""
Write-Host "Manual collect only:"
Write-Host "  `"$pythonExe`" `"$scriptPath`" --collect --skip-evolve"
