# run_daily_plus_pipeline.ps1
# Daily Plus 전체 파이프라인: 수집 -> GPT 세션 -> 대시보드 생성 -> git push
# Task Scheduler 또는 수동 실행 모두 지원

param(
    [switch]$SkipGitPush,
    [switch]$SkipGptSession,
    [switch]$ForceCollect
)

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path $PSScriptRoot -Parent
$scriptsDir = $PSScriptRoot
$pythonExe = (Get-Command python -ErrorAction SilentlyContinue)?.Source
if (-not $pythonExe) { $pythonExe = "python" }

$logDir = Join-Path $repoRoot "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$logFile = Join-Path $logDir "daily_plus_pipeline_$(Get-Date -Format 'yyyyMMdd').log"

function Log($msg) {
    $ts = Get-Date -Format "HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

function RunPython($script, $args, $label) {
    Log "START: $label"
    $fullPath = Join-Path $scriptsDir $script
    $result = & $pythonExe "-X" "utf8" $fullPath @args 2>&1
    $result | ForEach-Object { Log "  $_" }
    if ($LASTEXITCODE -ne 0) {
        Log "WARN: $label exited with code $LASTEXITCODE (continuing)"
        return $false
    }
    Log "OK: $label"
    return $true
}

Log "=== Daily Plus Pipeline START ==="
Log "Repo: $repoRoot"

# 1. ChatGPT Pulse 수집
$collectArgs = @("--collect", "--allow-recovery")
if ($ForceCollect) { $collectArgs += "--force" }
RunPython "chatgpt_daily_collector.py" $collectArgs "ChatGPT Pulse 수집"

# 2. GPT 세션 전체 수집 (Chrome이 열려있으면 skip)
if (-not $SkipGptSession) {
    RunPython "gpt_session_collector.py" @("--collect") "GPT 세션 수집"
} else {
    Log "SKIP: GPT 세션 수집 (-SkipGptSession)"
}

# 3. Daily Plus 대시보드 + 모닝 리포트 생성
$reportOk = RunPython "daily_plus_morning_report.py" @() "Daily Plus 대시보드 생성"

# 4. git push (대시보드 생성 성공 시)
if ($reportOk -and -not $SkipGitPush) {
    Log "START: git push"
    Push-Location $repoRoot
    try {
        $gitStatus = & git status --porcelain 2>&1
        if ($gitStatus) {
            & git add `
                "docs/daily-plus.html" `
                "ObsidianVault/04_Wiki/daily-plus/" `
                "ObsidianVault/00_UPGRADE/pulse-evolution/" `
                "ObsidianVault/01_RAW/gpt-sessions/" `
                "ObsidianVault/10_AgentBus/outbox/Bucky/" `
                "ObsidianVault/10_AgentBus/reports/" 2>&1 | ForEach-Object { Log "  git add: $_" }

            $dateStr = Get-Date -Format "yyyy-MM-dd"
            $commitMsg = "chore: Daily Plus 자동 업데이트 $dateStr [skip ci]"
            & git commit -m $commitMsg 2>&1 | ForEach-Object { Log "  git commit: $_" }
            & git push 2>&1 | ForEach-Object { Log "  git push: $_" }
            Log "OK: git push 완료"
        } else {
            Log "SKIP: 변경사항 없음, git push 생략"
        }
    } finally {
        Pop-Location
    }
} elseif ($SkipGitPush) {
    Log "SKIP: git push (-SkipGitPush)"
} else {
    Log "SKIP: 대시보드 생성 실패로 git push 생략"
}

Log "=== Daily Plus Pipeline END ==="
