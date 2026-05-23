# setup_claude_settings.ps1
# Claude Code 전체 설정을 현재 PC에 적용:
#   1. statusLine + Stop hook (context 경고)
#   2. Obsidian CLAUDE_MASTER.md → ~/.claude/CLAUDE.md 동기화
#
# 어느 PC에서든 PowerShell로 실행:
#   powershell -ExecutionPolicy Bypass -File "G:\내 드라이브\obsidian-agent-brain-system\scripts\setup_claude_settings.ps1"

$SETTINGS_PATH = "$env:USERPROFILE\.claude\settings.json"
$G_DRIVE = "G:/내 드라이브/obsidian-agent-brain-system/scripts"

$NEW_KEYS = @{
    statusLine = @{
        type    = "command"
        command = "python3 `"$G_DRIVE/claude_statusline.py`""
        padding = 0
    }
    hooks = @{
        Stop = @(
            @{
                matcher = ""
                hooks   = @(
                    @{
                        type    = "command"
                        command = "python3 `"$G_DRIVE/context_warning.py`""
                    }
                )
            }
        )
    }
}

# settings.json 로드 (없으면 빈 객체)
if (Test-Path $SETTINGS_PATH) {
    $raw = Get-Content $SETTINGS_PATH -Raw -Encoding UTF8
    $settings = $raw | ConvertFrom-Json
} else {
    New-Item -ItemType Directory -Force -Path (Split-Path $SETTINGS_PATH) | Out-Null
    $settings = New-Object PSCustomObject
}

# statusLine / hooks 병합 (덮어쓰기)
$settings | Add-Member -NotePropertyName "statusLine" -NotePropertyValue $NEW_KEYS.statusLine -Force
$settings | Add-Member -NotePropertyName "hooks"      -NotePropertyValue $NEW_KEYS.hooks      -Force

# 저장
$settings | ConvertTo-Json -Depth 10 | Out-File $SETTINGS_PATH -Encoding UTF8

Write-Host "[OK] $SETTINGS_PATH 업데이트 완료." -ForegroundColor Green
Write-Host "     Claude Code를 재시작하면 statusline + context 경고가 활성화됩니다."

# ── 2단계: CLAUDE.md 동기화 ────────────────────────────────────────────────────
Write-Host ""
Write-Host "[2/2] Obsidian CLAUDE_MASTER.md → CLAUDE.md 동기화 중..." -ForegroundColor Cyan

$SYNC_SCRIPT = "G:/내 드라이브/obsidian-agent-brain-system/scripts/sync_claude_instructions.py"
if (Test-Path $SYNC_SCRIPT) {
    $result = & python3 $SYNC_SCRIPT 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] CLAUDE.md 동기화 완료." -ForegroundColor Green
    } else {
        Write-Host "[WARN] CLAUDE.md 동기화 실패 — 수동으로 실행하세요: python3 $SYNC_SCRIPT" -ForegroundColor Yellow
        Write-Host $result
    }
} else {
    Write-Host "[WARN] sync_claude_instructions.py 없음 — G: 드라이브 마운트 확인 필요." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "설치 완료. Claude Code를 재시작하세요." -ForegroundColor Green
