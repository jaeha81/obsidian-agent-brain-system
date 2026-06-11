param(
  [Parameter(Mandatory = $true)]
  [string]$TaskId,

  [Parameter(Mandatory = $true)]
  [ValidateSet('user', 'claude', 'codex')]
  [string]$Speaker,

  [ValidateSet('done', 'cancelled', 'blocked')]
  [string]$Status = 'done',

  [string]$Body = ''
)

$ErrorActionPreference = 'Stop'

function Get-SharedRoot {
  $DriveName = -join @([char]0xB0B4, ' ', [char]0xB4DC, [char]0xB77C, [char]0xC774, [char]0xBE0C)
  return Join-Path (Join-Path 'G:\' $DriveName) 'JH-SHARED'
}

$Shared = Get-SharedRoot
$LocksRoot = Join-Path $Shared '05_TASK_LOCKS'
$ActiveRoot = Join-Path $LocksRoot 'active'
$DoneRoot = Join-Path (Join-Path $LocksRoot 'done') (Get-Date -Format 'yyyy-MM')
$LogsRoot = Join-Path $Shared '06_TASK_LOGS'
$LogDir = Join-Path $LogsRoot (Get-Date -Format 'yyyy-MM')
$ActivePath = Join-Path $ActiveRoot "$TaskId.json"
$DonePath = Join-Path $DoneRoot "$TaskId.json"
$LogPath = Join-Path $LogDir "$TaskId.jsonl"
$HostName = if ($env:COMPUTERNAME) { $env:COMPUTERNAME } else { 'unknown-pc' }

if (!(Test-Path $ActivePath)) {
  throw "Active task lock not found: $ActivePath"
}

New-Item -ItemType Directory -Path $DoneRoot -Force | Out-Null
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

$Lock = Get-Content -Encoding UTF8 -Raw $ActivePath | ConvertFrom-Json
$Lock | Add-Member -NotePropertyName status -NotePropertyValue $Status -Force
$Lock | Add-Member -NotePropertyName finishedAt -NotePropertyValue ((Get-Date).ToUniversalTime().ToString('o')) -Force
$Lock | Add-Member -NotePropertyName finishedBy -NotePropertyValue $Speaker -Force
$Lock | Add-Member -NotePropertyName finishedHost -NotePropertyValue $HostName -Force
($Lock | ConvertTo-Json -Depth 8) | Set-Content -Encoding UTF8 $DonePath
Remove-Item -LiteralPath $ActivePath -Force

$Record = [ordered]@{
  id = [guid]::NewGuid().ToString()
  taskId = $TaskId
  createdAt = (Get-Date).ToUniversalTime().ToString('o')
  speaker = $Speaker
  host = $HostName
  kind = 'finish'
  status = $Status
  body = $Body
}
($Record | ConvertTo-Json -Compress -Depth 8) | Add-Content -Encoding UTF8 $LogPath

Write-Host "Finished task: $TaskId"
Write-Host "Moved lock to: $DonePath"
