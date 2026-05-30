# Bucky Bot 자동시작 Task Scheduler 등록 스크립트
# 실행: PowerShell -ExecutionPolicy Bypass -File setup_autostart.ps1

$TaskName = "BuckyBotSupervisor"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BatFile = Join-Path $ScriptRoot "start_discord_bot.bat"
$LogFile = Join-Path $ScriptRoot "supervisor_autostart.log"

Write-Host "=== Bucky Bot Task Scheduler 등록 ===" -ForegroundColor Cyan
Write-Host "루트: $ScriptRoot"
Write-Host "배치: $BatFile"

if (-not (Test-Path $BatFile)) {
    Write-Host "ERROR: start_discord_bot.bat 없음 — $BatFile" -ForegroundColor Red
    exit 1
}

# 기존 태스크 제거
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "기존 태스크 제거 중..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# 액션: cmd /c "bat파일" >> 로그 2>&1
$Action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$BatFile`" >> `"$LogFile`" 2>&1"

# 트리거: 로그온 시 (현재 사용자)
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

# 설정: 숨김 창, 실패 시 1분 후 재시도, 무한 실행
$Settings = New-ScheduledTaskSettingsSet `
    -Hidden `
    -RestartCount 99 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew

# 최고 권한으로 실행
$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Highest

try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Principal $Principal `
        -Description "Bucky Discord Bot 슈퍼바이저 — 로그인 시 자동 시작" | Out-Null

    Write-Host "✅ Task Scheduler 등록 완료: '$TaskName'" -ForegroundColor Green
    Write-Host "   로그온 시 자동 시작됩니다."
    Write-Host ""
    Write-Host "지금 바로 시작하려면 아래 명령 실행:"
    Write-Host "  Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Yellow
} catch {
    Write-Host "❌ 등록 실패: $_" -ForegroundColor Red
    exit 1
}

# 현재 실행 중인 봇 확인
$running = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    try { (Get-WmiObject Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine -like "*discord_bot*" } catch { $false }
}

if ($running) {
    Write-Host ""
    Write-Host "⚠️  이미 실행 중인 봇 프로세스 감지됨 (PID: $($running.Id -join ', '))" -ForegroundColor Yellow
    Write-Host "   Task Scheduler로 전환하려면 기존 프로세스를 종료하고"
    Write-Host "   Start-ScheduledTask -TaskName '$TaskName' 를 실행하세요."
} else {
    $answer = Read-Host "지금 바로 봇을 시작할까요? (Y/N)"
    if ($answer -match "^[Yy]") {
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "✅ 봇 시작됨" -ForegroundColor Green
    }
}
