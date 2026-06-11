param(
  [Parameter(Mandatory = $true)]
  [ValidateSet('user', 'claude', 'codex')]
  [string]$Speaker,

  [Parameter(Mandatory = $true)]
  [ValidateSet('summary', 'change', 'issue', 'verification', 'remaining', 'handoff', 'next-check', 'note')]
  [string]$Kind,

  [Parameter(Mandatory = $true)]
  [string]$Body,

  [string]$Date = (Get-Date -Format 'yyyy-MM-dd'),
  [string]$Priority = '',
  [string]$Status = ''
)

$ErrorActionPreference = 'Stop'
$DriveName = -join @([char]0xB0B4, ' ', [char]0xB4DC, [char]0xB77C, [char]0xC774, [char]0xBE0C)
$Shared = Join-Path (Join-Path 'G:\' $DriveName) 'JH-SHARED'
$DailyRoot = Join-Path $Shared '04_DAILY_REPORTS'

$Year = $Date.Substring(0, 4)
$Month = $Date.Substring(0, 7)
$TargetDir = Join-Path (Join-Path $DailyRoot $Year) $Month
$EntriesDir = Join-Path $TargetDir "$Date.entries"
$SpeakerDir = Join-Path $EntriesDir $Speaker
$HostName = if ($env:COMPUTERNAME) { $env:COMPUTERNAME } else { 'unknown-pc' }
$SafeHostName = $HostName -replace '[^A-Za-z0-9._-]', '_'
$Target = Join-Path $SpeakerDir "$SafeHostName.jsonl"

New-Item -ItemType Directory -Path $SpeakerDir -Force | Out-Null

$Record = [ordered]@{
  id = [guid]::NewGuid().ToString()
  date = $Date
  createdAt = (Get-Date).ToUniversalTime().ToString('o')
  speaker = $Speaker
  host = $HostName
  kind = $Kind
  priority = $Priority
  status = $Status
  body = $Body
}

$Line = ($Record | ConvertTo-Json -Compress -Depth 5)
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$Stream = [System.IO.File]::Open($Target, [System.IO.FileMode]::Append, [System.IO.FileAccess]::Write, [System.IO.FileShare]::Read)
try {
  $Writer = New-Object System.IO.StreamWriter($Stream, $Utf8NoBom)
  try {
    $Writer.WriteLine($Line)
  } finally {
    $Writer.Dispose()
  }
} finally {
  $Stream.Dispose()
}

Write-Host "Added daily entry: $Target"

