param(
  [string[]]$Targets = @()
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
$ActiveRoot = Join-Path (Join-Path $Shared '05_TASK_LOCKS') 'active'
New-Item -ItemType Directory -Path $ActiveRoot -Force | Out-Null

$Locks = @()
$ActiveLockFiles = Get-ChildItem -Path $ActiveRoot -Filter '*.json' -File -ErrorAction SilentlyContinue
foreach ($LockFile in $ActiveLockFiles) {
  try {
    $Locks += Get-Content -Encoding UTF8 -Raw $LockFile.FullName | ConvertFrom-Json
  } catch {
    Write-Warning "Skipped unreadable lock: $($LockFile.FullName)"
  }
}

if ($Targets.Count -eq 0) {
  if ($Locks.Count -eq 0) {
    Write-Host 'No active task locks.'
    exit 0
  }
  $Locks | Select-Object taskId, owner, mode, title, host, startedAt, targets | Format-List
  exit 0
}

$Conflicts = @()
foreach ($Lock in $Locks) {
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

if ($Conflicts.Count -eq 0) {
  Write-Host 'No task conflicts detected.'
  exit 0
}

Write-Host 'Task conflicts detected.'
$Conflicts | ConvertTo-Json -Depth 6
exit 2
