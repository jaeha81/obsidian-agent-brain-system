param(
  [string]$TaskId = '',

  [Parameter(Mandatory = $true)]
  [ValidateSet('user', 'claude', 'codex')]
  [string]$Owner,

  [Parameter(Mandatory = $true)]
  [ValidateSet('implementation', 'review', 'coordination', 'sync')]
  [string]$Mode,

  [Parameter(Mandatory = $true)]
  [string]$Title,

  [Parameter(Mandatory = $true)]
  [string[]]$Targets,

  [string]$Body = '',
  [switch]$Force
)

$ErrorActionPreference = 'Stop'

function Get-SharedRoot {
  $DriveName = -join @([char]0xB0B4, ' ', [char]0xB4DC, [char]0xB77C, [char]0xC774, [char]0xBE0C)
  return Join-Path (Join-Path 'G:\' $DriveName) 'JH-SHARED'
}

function Normalize-Target {
  param([string]$Value)
  return ($Value.Trim().TrimEnd('\', '/') -replace '/', '\').ToLowerInvariant()
}

function Test-TargetOverlap {
  param([string]$Left, [string]$Right)
  $A = Normalize-Target $Left
  $B = Normalize-Target $Right
  return ($A -eq $B -or $A.StartsWith("$B\") -or $B.StartsWith("$A\"))
}

$Shared = Get-SharedRoot
$LocksRoot = Join-Path $Shared '05_TASK_LOCKS'
$ActiveRoot = Join-Path $LocksRoot 'active'
$LogsRoot = Join-Path $Shared '06_TASK_LOGS'
New-Item -ItemType Directory -Path $ActiveRoot -Force | Out-Null
New-Item -ItemType Directory -Path $LogsRoot -Force | Out-Null

if ([string]::IsNullOrWhiteSpace($TaskId)) {
  $TaskId = "$(Get-Date -Format 'yyyy-MM-dd-HHmmss')-$Owner-$Mode"
}

$HostName = if ($env:COMPUTERNAME) { $env:COMPUTERNAME } else { 'unknown-pc' }
$StartedAt = (Get-Date).ToUniversalTime().ToString('o')
$Conflicts = @()

$ActiveLocks = Get-ChildItem -Path $ActiveRoot -Filter '*.json' -File -ErrorAction SilentlyContinue
foreach ($LockFile in $ActiveLocks) {
  try {
    $Lock = Get-Content -Encoding UTF8 -Raw $LockFile.FullName | ConvertFrom-Json
  } catch {
    continue
  }
  if ($Lock.taskId -eq $TaskId) {
    continue
  }
  foreach ($ExistingTarget in @($Lock.targets)) {
    foreach ($Target in $Targets) {
      if (Test-TargetOverlap $ExistingTarget $Target) {
        $Conflicts += [ordered]@{
          taskId = $Lock.taskId
          owner = $Lock.owner
          mode = $Lock.mode
          target = $ExistingTarget
          requestedTarget = $Target
          title = $Lock.title
        }
      }
    }
  }
}

if ($Conflicts.Count -gt 0 -and !$Force) {
  Write-Host 'Task conflict detected. Use -Force only after user approval.'
  $Conflicts | ConvertTo-Json -Depth 6
  exit 2
}

$LockPath = Join-Path $ActiveRoot "$TaskId.json"
$Lock = [ordered]@{
  taskId = $TaskId
  owner = $Owner
  mode = $Mode
  title = $Title
  body = $Body
  host = $HostName
  startedAt = $StartedAt
  status = 'active'
  targets = @($Targets)
  conflictsAtStart = @($Conflicts)
}

$Json = $Lock | ConvertTo-Json -Depth 8
try {
  $Stream = [System.IO.File]::Open($LockPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::Read)
  try {
    $Writer = New-Object System.IO.StreamWriter($Stream, [System.Text.UTF8Encoding]::new($true))
    try {
      $Writer.Write($Json)
    } finally {
      $Writer.Dispose()
    }
  } finally {
    $Stream.Dispose()
  }
} catch {
  throw "Task lock already exists or cannot be created: $LockPath"
}

$LogMonth = Get-Date -Format 'yyyy-MM'
$LogDir = Join-Path $LogsRoot $LogMonth
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$LogPath = Join-Path $LogDir "$TaskId.jsonl"
$LogRecord = [ordered]@{
  id = [guid]::NewGuid().ToString()
  taskId = $TaskId
  createdAt = $StartedAt
  speaker = $Owner
  host = $HostName
  kind = 'start'
  body = $Title
  targets = @($Targets)
}
($LogRecord | ConvertTo-Json -Compress -Depth 8) | Add-Content -Encoding UTF8 $LogPath

Write-Host "Started task: $TaskId"
Write-Host "Lock: $LockPath"
Write-Host "Log: $LogPath"
