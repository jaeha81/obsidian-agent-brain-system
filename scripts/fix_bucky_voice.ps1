# Bucky + Voice(ffmpeg) recovery script.
# Run on the HOME PC, as the same user that runs the bot.
#   powershell -ExecutionPolicy Bypass -File "G:\<drive>\obsidian-agent-brain-system\fix_bucky_voice.ps1"
# It locates claude/ffmpeg, appends a PATH fix to .env (backup first), verifies, then restarts the bot.

$ErrorActionPreference = 'Continue'
$root = $PSScriptRoot
if (-not $root) { $root = Split-Path -Parent $MyInvocation.MyCommand.Definition }
$envFile = Join-Path $root '.env'
Write-Host "root    = $root"
Write-Host "envFile = $envFile"
if (-not (Test-Path $envFile)) { Write-Host 'ERROR: .env not found next to this script. Abort.' -ForegroundColor Red; return }

Write-Host '--- [1/5] locate claude / ffmpeg ---'
$claude = (Get-Command claude.cmd -ErrorAction SilentlyContinue).Source
if (-not $claude) { $claude = (Get-Command claude -ErrorAction SilentlyContinue).Source }
if (-not $claude) { $p = Join-Path $env:APPDATA 'npm\claude.cmd'; if (Test-Path $p) { $claude = $p } }
$ffmpeg = (Get-Command ffmpeg.exe -ErrorAction SilentlyContinue).Source
if (-not $ffmpeg) { $ffmpeg = (Get-Command ffmpeg -ErrorAction SilentlyContinue).Source }
Write-Host "  claude = $claude"
Write-Host "  ffmpeg = $ffmpeg"
if (-not $claude -and -not $ffmpeg) { Write-Host 'ERROR: neither claude nor ffmpeg on PATH. Check install. Abort.' -ForegroundColor Red; return }

Write-Host '--- [2/5] backup .env ---'
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
Copy-Item $envFile "$envFile.bak_$stamp" -Force
Write-Host "  backup: $envFile.bak_$stamp"

Write-Host '--- [3/5] patch .env (append-only, existing lines untouched) ---'
$marker = '# --- bucky path/cmd fix ---'
$raw = Get-Content $envFile -Raw
if ($raw -match [regex]::Escape($marker)) {
  Write-Host '  already patched, skip'
} else {
  $dirs = @()
  if ($claude) { $dirs += Split-Path -Parent $claude }
  if ($ffmpeg) { $dirs += Split-Path -Parent $ffmpeg }
  $dirs = $dirs | Select-Object -Unique
  $lines = @($marker)
  if ($dirs.Count -gt 0) { $lines += ('PATH=${PATH};' + ($dirs -join ';')) }
  if ($claude) { $lines += ('CLAUDE_COMMAND=' + $claude) }
  $lines += 'BUCKY_TIMEOUT_CODE=600'
  Add-Content -Path $envFile -Value ("`r`n" + ($lines -join "`r`n"))
  Write-Host '  added:'
  $lines | ForEach-Object { Write-Host "    $_" }
}

Write-Host '--- [4/5] verify (strip PATH, load .env, resolve) ---'
python -c "import os; os.environ['PATH']=r'C:\Windows\System32'; from dotenv import load_dotenv; load_dotenv(r'$envFile', override=True); import shutil; print('  claude ->', shutil.which('claude.cmd') or shutil.which('claude')); print('  ffmpeg ->', shutil.which('ffmpeg'))"

Write-Host '--- [5/5] restart signal ---'
$sigdir = Join-Path $root 'ObsidianVault\10_AgentBus\signals'
New-Item -ItemType Directory -Force -Path $sigdir | Out-Null
Set-Content -Path (Join-Path $sigdir 'bot_restart.signal') -Value (Get-Date -Format o)
Write-Host '  restart signal written; supervisor restarts bot within ~10s'
Write-Host ''
Write-Host '>> Wait 1-2 min, then test in Discord: (1) send a voice message (2) ask Bucky a question' -ForegroundColor Green
Write-Host '>> To revert: copy the .env.bak_* back over .env'
