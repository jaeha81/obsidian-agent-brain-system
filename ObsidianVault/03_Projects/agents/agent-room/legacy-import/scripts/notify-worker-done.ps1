# notify-worker-done.ps1
# Boris Phase 2-B: append a worker completion signal for a parallel session.
#
# Usage:
#   .\notify-worker-done.ps1 -TaskId "TASK-20260502-134420" -Session "B" -Area "frontend"
#   .\notify-worker-done.ps1 -TaskId "TASK-20260502-134420" -Session "C" -Area "backend" -Status blocked -VerifyPassed:$false -Body "API contract changed"
#   .\notify-worker-done.ps1 -TaskId "TASK-20260502-134420" -Session "B" -Area "frontend" -DryRun

param(
  [Parameter(Mandatory = $true)]
  [string]$TaskId,

  [Parameter(Mandatory = $true)]
  [string]$Session,

  [string]$Area = '',

  [ValidateSet('done', 'blocked', 'cancelled')]
  [string]$Status = 'done',

  [bool]$VerifyPassed = $true,

  [ValidateSet('claude', 'codex', 'user')]
  [string]$Speaker = 'claude',

  [string]$Body = '',

  [string]$AssignmentFile = '',

  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

function Get-SharedRoot {
  $DriveName = -join @([char]0xB0B4, ' ', [char]0xB4DC, [char]0xB77C, [char]0xC774, [char]0xBE0C)
  return Join-Path (Join-Path 'G:\' $DriveName) 'JH-SHARED'
}

function Find-AssignmentFile {
  param(
    [string]$SystemDir,
    [string]$TaskId
  )

  Get-ChildItem -LiteralPath $SystemDir -Filter 'parallel-session-*.md' -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Where-Object {
      try {
        (Get-Content -LiteralPath $_.FullName -Raw -Encoding UTF8) -match [regex]::Escape($TaskId)
      } catch {
        $false
      }
    } |
    Select-Object -First 1 -ExpandProperty FullName
}

function Update-AssignmentStatus {
  param(
    [string]$Path,
    [string]$Session,
    [string]$Area,
    [string]$Status,
    [string]$FinishedAt
  )

  if (!(Test-Path -LiteralPath $Path)) { return $false }

  $content = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
  $sessionLabel = if ($Session -match '^Session\s+') { $Session } else { "Session $Session" }
  $statusText = "``$Status``"
  $areaPattern = if ($Area) { [regex]::Escape($Area) } else { '[^|]+' }
  $pattern = "(?m)^\|\s*$([regex]::Escape($sessionLabel))\s*\|\s*($areaPattern)\s*\|\s*``[^`]+``\s*\|\s*[^|]*\|$"
  $replacement = "| $sessionLabel | `$2 | $statusText | $FinishedAt |"

  $updated = [regex]::Replace($content, $pattern, $replacement, 1)
  if ($updated -eq $content) { return $false }

  Set-Content -LiteralPath $Path -Encoding UTF8 -Value $updated
  return $true
}

$Shared = Get-SharedRoot
$SystemDir = Join-Path $Shared '00_SYSTEM'
$AgentRoomDir = Join-Path $Shared '01_AGENT_ROOM'
$LogsRoot = Join-Path $Shared '06_TASK_LOGS'
$LogDir = Join-Path $LogsRoot (Get-Date -Format 'yyyy-MM')
$AgentRoomLog = Join-Path $AgentRoomDir 'agent-room-messages.jsonl'
$TaskLog = Join-Path $LogDir "$TaskId.jsonl"
$HostName = if ($env:COMPUTERNAME) { $env:COMPUTERNAME } else { 'unknown-pc' }
$NowUtc = (Get-Date).ToUniversalTime().ToString('o')
$FinishedAt = Get-Date -Format 'yyyy-MM-dd HH:mm'

New-Item -ItemType Directory -Path $AgentRoomDir -Force | Out-Null
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

if (!$AssignmentFile) {
  $AssignmentFile = Find-AssignmentFile -SystemDir $SystemDir -TaskId $TaskId
}

$Signal = [ordered]@{
  taskId = $TaskId
  session = $Session
  status = $Status
  area = $Area
  timestamp = $NowUtc
  verifyPassed = $VerifyPassed
  host = $HostName
  body = $Body
}

$TaskRecord = [ordered]@{
  id = [guid]::NewGuid().ToString()
  taskId = $TaskId
  createdAt = $NowUtc
  speaker = $Speaker
  host = $HostName
  kind = if ($Status -eq 'done' -and $VerifyPassed) { 'verification' } else { 'issue' }
  status = $Status
  body = ($Signal | ConvertTo-Json -Compress -Depth 8)
}

$Summary = "Parallel worker signal: taskId=$TaskId session=$Session status=$Status"
if ($Area) { $Summary += " area=$Area" }
if ($VerifyPassed) { $Summary += " verifyPassed=true" } else { $Summary += " verifyPassed=false" }
if ($Body) { $Summary += " body=$Body" }

$AgentRoomRecord = [ordered]@{
  id = [guid]::NewGuid().ToString()
  ts = $NowUtc
  speaker = $Speaker
  kind = 'implementation'
  target = 'room'
  status = $Status
  body = $Summary
}

$assignmentUpdated = $false
if ($AssignmentFile -and !$DryRun) {
  $assignmentUpdated = Update-AssignmentStatus -Path $AssignmentFile -Session $Session -Area $Area -Status $Status -FinishedAt $FinishedAt
}

if ($DryRun) {
  Write-Host "Dry run only. No files were written."
  Write-Host "Task record:"
  $TaskRecord | ConvertTo-Json -Depth 8
  Write-Host "Agent Room record:"
  $AgentRoomRecord | ConvertTo-Json -Depth 8
  if ($AssignmentFile) { Write-Host "Assignment file candidate: $AssignmentFile" }
  exit 0
}

($TaskRecord | ConvertTo-Json -Compress -Depth 8) | Add-Content -Encoding UTF8 -LiteralPath $TaskLog
($AgentRoomRecord | ConvertTo-Json -Compress -Depth 8) | Add-Content -Encoding UTF8 -LiteralPath $AgentRoomLog

Write-Host "Worker signal appended."
Write-Host "Task log: $TaskLog"
Write-Host "Agent Room log: $AgentRoomLog"
if ($AssignmentFile) {
  Write-Host "Assignment file: $AssignmentFile"
  Write-Host "Assignment status updated: $assignmentUpdated"
} else {
  Write-Host "Assignment file not found for taskId: $TaskId"
}
