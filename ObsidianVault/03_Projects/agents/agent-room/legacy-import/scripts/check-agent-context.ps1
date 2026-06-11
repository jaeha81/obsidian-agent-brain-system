$ErrorActionPreference = 'Stop'

$Shared = 'G:\내 드라이브\JH-SHARED'
$RequiredFiles = @(
  '00_SYSTEM\agent-onboarding.md',
  '00_SYSTEM\sync-protocol.md',
  '00_SYSTEM\jh-system.md',
  '00_SYSTEM\paths.md',
  '02_HANDOFF\claude-sync-context-guard.md'
)

Write-Host '[JH Agent Context Check]'
Write-Host "PC: $env:COMPUTERNAME / User: $env:USERNAME"
Write-Host "Shared: $Shared"
Write-Host ''

$Missing = @()
foreach ($File in $RequiredFiles) {
  $Path = Join-Path $Shared $File
  if (Test-Path $Path) {
    $Item = Get-Item $Path
    Write-Host "OK   $File  ($($Item.LastWriteTime))"
  } else {
    Write-Host "MISS $File"
    $Missing += $File
  }
}

Write-Host ''
if ($Missing.Count -gt 0) {
  Write-Host 'Result: FAIL - required shared context files are missing.'
  exit 1
}

Write-Host 'Result: PASS'
Write-Host 'JH 전제 확인 완료: 역할 분담, 저장소 분리, 동기화 최소 컨텍스트 규칙을 확인했습니다.'
Write-Host '다음 단계: Agent Room에서 동기화 또는 업데이트를 눌러 현재 PC 스냅샷을 기록하세요.'
