# setup_scheduler.ps1
# Windows 작업 스케줄러에 Brain Evolution Collection Pipeline 등록
# 매일 오전 9시 자동 실행
# 실행: powershell -ExecutionPolicy Bypass -File scripts\setup_scheduler.ps1

$TaskName = "BrainEvolution-CollectionPipeline"
$PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) {
    Write-Error "Python을 찾을 수 없습니다. PATH에 Python이 설치되어 있어야 합니다."
    exit 1
}

$ScriptPath = Join-Path $PSScriptRoot "collection_pipeline.py"
if (-not (Test-Path $ScriptPath)) {
    Write-Error "collection_pipeline.py를 찾을 수 없습니다: $ScriptPath"
    exit 1
}

$LogPath = Join-Path $PSScriptRoot "pipeline_scheduler.log"

# 기존 태스크 제거 (있으면)
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "기존 태스크 제거됨."
}

# 태스크 액션: python collection_pipeline.py
$Action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "`"$ScriptPath`"" `
    -WorkingDirectory (Split-Path $ScriptPath)

# 트리거: 매일 오전 9시
$Trigger = New-ScheduledTaskTrigger -Daily -At "09:00"

# 설정: 네트워크 없어도 실행, 배터리 무관, 5분 지연 후 재시도
$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew

# 등록
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Bucky Brain Evolution: GPT+Claude 세션 수집 → 지식 정제 → 갭 분석" `
    -RunLevel Highest

if ($?) {
    Write-Host ""
    Write-Host "✅ 작업 스케줄러 등록 완료: '$TaskName'"
    Write-Host "   실행 시각: 매일 오전 09:00"
    Write-Host "   스크립트: $ScriptPath"
    Write-Host ""
    Write-Host "수동 실행 테스트:"
    Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
} else {
    Write-Error "등록 실패. 관리자 권한으로 실행했는지 확인하세요."
}
