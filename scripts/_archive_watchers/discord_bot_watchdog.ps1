param(
    [int]$CheckIntervalSeconds = 30,
    [int]$RestartDelaySeconds = 10
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Supervisor = Join-Path $Root "scripts\bucky_bot_supervisor.py"

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:BUCKY_SUPERVISOR_INTERVAL = [string]$CheckIntervalSeconds
$env:BUCKY_SUPERVISOR_RESTART_DELAY = [string]$RestartDelaySeconds

$Python = "C:\Python314\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

Write-Host "[Bucky] Starting canonical supervisor: $Supervisor"
& $Python -X utf8 $Supervisor
exit $LASTEXITCODE
