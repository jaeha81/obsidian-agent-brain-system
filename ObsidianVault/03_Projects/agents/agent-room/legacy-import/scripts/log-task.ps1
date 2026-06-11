param(
  [Parameter(Mandatory = $true)]
  [string]$TaskId,

  [Parameter(Mandatory = $true)]
  [ValidateSet('user', 'claude', 'codex')]
  [string]$Speaker,

  [Parameter(Mandatory = $true)]
  [ValidateSet('note', 'decision', 'implementation', 'review', 'issue', 'verification', 'handoff')]
  [string]$Kind,

  [Parameter(Mandatory = $true)]
  [string]$Body
)

$ErrorActionPreference = 'Stop'

function Get-SharedRoot {
  $DriveName = -join @([char]0xB0B4, ' ', [char]0xB4DC, [char]0xB77C, [char]0xC774, [char]0xBE0C)
  return Join-Path (Join-Path 'G:\' $DriveName) 'JH-SHARED'
}

$Shared = Get-SharedRoot
$LogsRoot = Join-Path $Shared '06_TASK_LOGS'
$LogMonth = Get-Date -Format 'yyyy-MM'
$LogDir = Join-Path $LogsRoot $LogMonth
$LogPath = Join-Path $LogDir "$TaskId.jsonl"
$HostName = if ($env:COMPUTERNAME) { $env:COMPUTERNAME } else { 'unknown-pc' }

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

$Record = [ordered]@{
  id = [guid]::NewGuid().ToString()
  taskId = $TaskId
  createdAt = (Get-Date).ToUniversalTime().ToString('o')
  speaker = $Speaker
  host = $HostName
  kind = $Kind
  body = $Body
}

($Record | ConvertTo-Json -Compress -Depth 8) | Add-Content -Encoding UTF8 $LogPath
Write-Host "Logged task entry: $LogPath"
