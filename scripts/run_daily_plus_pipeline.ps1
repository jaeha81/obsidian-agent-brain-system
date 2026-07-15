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
$_pyCmd = Get-Command python -ErrorAction SilentlyContinue
$pythonExe = if ($_pyCmd) { $_pyCmd.Source } else { "python" }

$logDir = Join-Path $repoRoot "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$logFile = Join-Path $logDir "daily_plus_pipeline_$(Get-Date -Format 'yyyyMMdd').log"

function Log($msg) {
    $ts = Get-Date -Format "HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

function RunPython($script, $scriptArgs, $label) {
    Log "START: $label"
    $fullPath = Join-Path $scriptsDir $script
    $result = & $pythonExe "-X" "utf8" $fullPath @scriptArgs 2>&1
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

# 3b. System Evolution 대시보드 데이터 생성 (Daily Plus 수집과 독립)
RunPython "build_system_evolution.py" @() "System Evolution 생성"

# 3c. Charlie 시스템 감사 (읽기 전용 점검 — 결과 JSON 생성, 커밋은 아래 4단계가 수행)
RunPython "charlie_audit.py" @() "Charlie 감사"

# 3d. Brain Status 생성 (오라클 읽기전용 + usage + policy shadow + agents.yaml, Stage 21)
# 실배포(오라클 #2)에선 라이브 태스크 큐가 #2에 쌓인다(split-brain). 키가 있는 머신에서만
# 원격 집계를 켠다 — 키 없으면 env 미설정 → 생성기가 로컬 DB로 degrade(대시보드는 항상 렌더).
$_oracleKey = Join-Path $HOME ".ssh\oci-bucky-a1"
if (Test-Path $_oracleKey) {
    $env:BUCKY_ORACLE_SSH = "ubuntu@161.33.204.158"
    $env:BUCKY_ORACLE_SSH_KEY = $_oracleKey
}
RunPython "generate_brain_status.py" @() "Brain Status 생성"

# 3e. 매일 갱신되지 않던 상태 대시보드 편입 (모두 로컬 데이터, 집PC/외부/유료 의존 없음)
#     - AI사용량: 매일 재생성 / 워크플로우: 매일 재생성
#     - 시스템강화(sync_system_enhance): career-strategy 소스가 바뀔 때만 자체 갱신(자가 가드)
RunPython "generate_ai_usage_dashboard.py" @() "AI 사용량 대시보드 생성"
RunPython "build_workflow_data.py" @() "워크플로우 데이터 생성"
RunPython "sync_system_enhance.py" @() "시스템 강화 동기화"

# 4. git push (대시보드 생성 성공 시)
if ($reportOk -and -not $SkipGitPush) {
    Log "START: git push"
    Push-Location $repoRoot
    try {
        $gitStatus = & git status --porcelain 2>&1
        if ($gitStatus) {
            & git add `
                "docs/daily-plus.html" `
                "docs/daily-plus/index.html" `
                "docs/system-evolution.html" `
                "docs/data/system_evolution.json" `
                "docs/data/charlie_status.json" `
                "docs/bucky-brain.html" `
                "docs/org-structure.html" `
                "docs/data/bucky_brain_status.json" `
                "docs/data/agents_org.json" `
                "docs/ai-usage.html" `
                "docs/workflow/agents.json" `
                "docs/workflow/health.json" `
                "docs/data/system_enhance.json" `
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
