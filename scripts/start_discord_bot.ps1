param(
    [switch]$Wait = $false
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Supervisor = Join-Path $Root "scripts\bucky_bot_supervisor.py"
$LogDir = Join-Path $Root ".logs"
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$Python = "C:\Python314\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

if ($Wait) {
    Write-Host "[Bucky] Starting supervisor in foreground: $Supervisor"
    & $Python -X utf8 $Supervisor
    exit $LASTEXITCODE
}

$psi = [System.Diagnostics.ProcessStartInfo]::new()
$psi.FileName = $Python
$psi.Arguments = "-X utf8 `"$Supervisor`""
$psi.WorkingDirectory = $Root
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$psi.RedirectStandardOutput = $false
$psi.RedirectStandardError = $false

foreach ($key in @($psi.Environment.Keys)) {
    if ($key -ieq "path" -and $key -cne "PATH") {
        $psi.Environment.Remove($key) | Out-Null
    }
}
$psi.Environment["PYTHONUTF8"] = "1"
$psi.Environment["PYTHONIOENCODING"] = "utf-8"

$process = [System.Diagnostics.Process]::Start($psi)

Write-Host "[Bucky] Supervisor PID: $($process.Id)"
Write-Host "[Bucky] Bot logs: $(Join-Path $Root 'discord_bot.log') / $(Join-Path $Root 'discord_bot.err')"
