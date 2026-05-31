param(
    [int]$CheckIntervalSeconds = 30,
    [int]$RestartDelaySeconds = 10
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Script = Join-Path $Root "scripts\discord_bot.py"
$LogDir = Join-Path $Root ".logs"

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

function Write-WatchdogLog {
    param([string]$Message)
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Message"
}

function Start-BotProcess {
    $ts = Get-Date -Format "yyyyMMdd_HHmmss"
    $logOut = Join-Path $LogDir "discord_bot_out_$ts.log"
    $logErr = Join-Path $LogDir "discord_bot_err_$ts.log"
    $proc = Start-Process `
        -FilePath "python" `
        -ArgumentList @("-X", "utf8", $Script) `
        -WorkingDirectory $Root `
        -RedirectStandardOutput $logOut `
        -RedirectStandardError $logErr `
        -PassThru `
        -WindowStyle Hidden
    Write-WatchdogLog "Bot started pid=$($proc.Id) log=$(Split-Path -Leaf $logOut)"
    return $proc
}

function Remove-OldLogs {
    Get-ChildItem $LogDir -Filter "discord_bot_*.log" -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } |
        Remove-Item -Force -ErrorAction SilentlyContinue
}

Write-WatchdogLog "Watchdog starting check=${CheckIntervalSeconds}s restart_delay=${RestartDelaySeconds}s"
Remove-OldLogs
$botProc = Start-BotProcess

while ($true) {
    Start-Sleep -Seconds $CheckIntervalSeconds
    if ($botProc -eq $null -or $botProc.HasExited) {
        $exitCode = if ($botProc) { $botProc.ExitCode } else { "?" }
        Write-WatchdogLog "Bot exited exit=$exitCode; restarting in ${RestartDelaySeconds}s"
        Start-Sleep -Seconds $RestartDelaySeconds
        Remove-OldLogs
        $botProc = Start-BotProcess
    }
}
