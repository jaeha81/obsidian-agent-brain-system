# create-parallel-session.ps1
# Boris Phase 2-B: 병렬 세션 배정 파일 생성 + Task Lock 등록 자동화
#
# 사용법:
#   .\create-parallel-session.ps1 -Title "작업명" -Areas "frontend","backend","test"
#   .\create-parallel-session.ps1 -Title "auth 리팩토링" -Areas "frontend","backend" -FileCount 15 -EstimatedHours 3
#
# 결과:
#   1. 00_SYSTEM/parallel-session-YYYYMMDD-HHMMSS.md 생성
#   2. Task Lock 등록 (start-task.ps1 호출)
#   3. 워커 온보딩 지시 출력

param(
    [Parameter(Mandatory = $true)]
    [string]$Title,

    [Parameter(Mandatory = $true)]
    [string[]]$Areas,

    [int]$FileCount = 0,
    [int]$EstimatedHours = 0
)

$ErrorActionPreference = 'Stop'

# ── 경로 설정 ──────────────────────────────────────────────
$SharedRoot = 'G:\내 드라이브\JH-SHARED'
$SystemDir  = Join-Path $SharedRoot '00_SYSTEM'
$Template   = Join-Path $SystemDir 'parallel-session-template.md'
$ScriptsDir = $PSScriptRoot

# ── 타임스탬프 ─────────────────────────────────────────────
$Now       = Get-Date
$Stamp     = $Now.ToString('yyyyMMdd-HHmmss')
$TaskId    = "TASK-$Stamp"
$KSTStr    = $Now.ToString('yyyy-MM-dd HH:mm') + ' KST'

# ── 배정 파일 경로 ──────────────────────────────────────────
$OutFile = Join-Path $SystemDir "parallel-session-$Stamp.md"

# ── 진입 판단 근거 문자열 ───────────────────────────────────
$FileCountStr = if ($FileCount -gt 0) { "$FileCount개 (10개 이상 OK)" } else { "미입력 — 직접 확인 필요" }
$HoursStr     = if ($EstimatedHours -gt 0) { "${EstimatedHours}시간 (2시간 이상 OK)" } else { "미입력 — 직접 확인 필요" }
$AreaCount    = $Areas.Count
$AreaCountStr = "$AreaCount개 (2개 이상 $(if ($AreaCount -ge 2) { 'OK' } else { 'NG' }))"

# ── 세션 레이블 (B, C, D, ...) ─────────────────────────────
$SessionLabels = @('B','C','D','E','F','G')

# ── 영역별 섹션 생성 ────────────────────────────────────────
$AreaSections = ''
for ($i = 0; $i -lt $Areas.Count; $i++) {
    $Label = if ($i -lt $SessionLabels.Count) { $SessionLabels[$i] } else { "X$i" }
    $Area  = $Areas[$i]
    $AreaSections += @"

### Session $Label — $Area

**담당 파일 목록 (이 목록 외 수정 불가):**
```
[파일 목록 직접 입력]
```

**작업 내용:**
- [ ] [구체적 작업 1]
- [ ] [구체적 작업 2]

**완료 조건:** [검증 기준]

**의존성:** 없음

---
"@
}

# ── 진행 상태 표 ────────────────────────────────────────────
$StatusRows = ''
for ($i = 0; $i -lt $Areas.Count; $i++) {
    $Label = if ($i -lt $SessionLabels.Count) { $SessionLabels[$i] } else { "X$i" }
    $StatusRows += "| Session $Label | $($Areas[$i]) | ``pending`` | — |`n"
}
$StatusRows += "| Session A | 공유+통합 | ``in-progress`` | — |"

# ── 워커 온보딩 지시 블록 ───────────────────────────────────
$OnboardingBlocks = ''
for ($i = 0; $i -lt $Areas.Count; $i++) {
    $Label = if ($i -lt $SessionLabels.Count) { $SessionLabels[$i] } else { "X$i" }
    $OnboardingBlocks += @"

**Session $Label ($($Areas[$i])):**
``````
이 파일을 읽어: $OutFile
너는 Session $Label 야. ~/.claude/guides/parallel-worker.md 가이드를 따라 진행해.
``````
"@
}

# ── 배정 파일 내용 생성 ─────────────────────────────────────
$Content = @"
# 병렬 세션 배정 파일

> 생성: create-parallel-session.ps1 자동 생성
> 오케스트레이터 가이드: ``~/.claude/guides/parallel-orchestrator.md``

---

## 기본 정보

| 필드 | 값 |
|------|-----|
| taskId | ``$TaskId`` |
| 작업명 | $Title |
| 오케스트레이터 | Session A |
| 생성 시각 | $KSTStr |
| 상태 | ``active`` |

---

## 진입 판단 근거

- 수정 예상 파일 수: $FileCountStr
- 독립 영역 수: $AreaCountStr
- 예상 소요 시간: $HoursStr

---

## 영역별 배정
$AreaSections

### Session A — 공유 파일 + 통합

**직접 처리 파일 (워커 배정 금지):**
```
[공유 파일 목록 직접 입력 — types, constants 등]
```

---

## 진행 상태

| 세션 | 영역 | 상태 | 완료 시각 |
|------|------|------|---------|
$StatusRows

---

## 워커 온보딩 지시
$OnboardingBlocks

---

## 완료 신호 형식 (Agent Room append)

```json
{"taskId":"$TaskId","session":"B","status":"done","area":"[영역명]","timestamp":"ISO8601","verifyPassed":true}
```

---

## 메모 / 이슈

<!-- 오케스트레이터가 진행 중 발견한 이슈, 결정 사항을 여기에 기록 -->
"@

# ── 파일 저장 ───────────────────────────────────────────────
$Content | Out-File -FilePath $OutFile -Encoding utf8
Write-Host "✅ 배정 파일 생성: $OutFile" -ForegroundColor Green

# ── Task Lock 등록 ──────────────────────────────────────────
$StartTaskScript = Join-Path $ScriptsDir 'start-task.ps1'
if (Test-Path $StartTaskScript) {
    $TargetPaths = $Areas | ForEach-Object { "parallel:$_" }
    try {
        & $StartTaskScript `
            -TaskId $TaskId `
            -Owner 'claude' `
            -Mode 'coordination' `
            -Title $Title `
            -Targets $TargetPaths
        Write-Host "✅ Task Lock 등록: $TaskId" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Task Lock 등록 실패 (수동 등록 필요): $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  start-task.ps1 없음 — Task Lock 수동 등록 필요" -ForegroundColor Yellow
}

# ── 워커 온보딩 출력 ────────────────────────────────────────
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "  병렬 세션 준비 완료 — 워커 세션 시작 지시" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

for ($i = 0; $i -lt $Areas.Count; $i++) {
    $Label = if ($i -lt $SessionLabels.Count) { $SessionLabels[$i] } else { "X$i" }
    Write-Host "[ Session $Label — $($Areas[$i]) ]" -ForegroundColor Yellow
    Write-Host "이 파일을 읽어: $OutFile"
    Write-Host "너는 Session $Label 야. ~/.claude/guides/parallel-worker.md 가이드를 따라 진행해."
    Write-Host ""
}

Write-Host "배정 파일에 파일 목록 직접 입력 후 워커 세션 시작하세요." -ForegroundColor Gray
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
