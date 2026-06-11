param(
  [string]$Date = (Get-Date -Format 'yyyy-MM-dd'),
  [string]$Author = 'Codex'
)

$ErrorActionPreference = 'Stop'
$Shared = 'G:\내 드라이브\JH-SHARED'
$DailyRoot = Join-Path $Shared '04_DAILY_REPORTS'
$Template = Join-Path $DailyRoot 'TEMPLATE.md'

if (!(Test-Path $Template)) {
  throw "Daily report template not found: $Template"
}

$Year = $Date.Substring(0, 4)
$Month = $Date.Substring(0, 7)
$TargetDir = Join-Path (Join-Path $DailyRoot $Year) $Month
$Target = Join-Path $TargetDir "$Date.md"
$EntriesDir = Join-Path $TargetDir "$Date.entries"

New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
New-Item -ItemType Directory -Path $EntriesDir -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $EntriesDir 'user') -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $EntriesDir 'claude') -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $EntriesDir 'codex') -Force | Out-Null

if (Test-Path $Target) {
  Write-Host "Daily report already exists: $Target"
  Write-Host "Entries directory ready: $EntriesDir"
  exit 0
}

$Content = Get-Content -Encoding UTF8 $Template -Raw
$Content = $Content.Replace('{{DATE}}', $Date).Replace('{{AUTHOR}}', $Author)
Set-Content -Encoding UTF8 $Target $Content
Write-Host "Created daily report: $Target"
Write-Host "Entries directory ready: $EntriesDir"

