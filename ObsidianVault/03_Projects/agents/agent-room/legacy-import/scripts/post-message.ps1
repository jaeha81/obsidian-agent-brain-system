param(
  [Parameter(Mandatory=$true)]
  [ValidateSet('claude','codex','user')]
  [string]$Speaker,

  [Parameter(Mandatory=$true)]
  [ValidateSet('direction','implementation','review','sync')]
  [string]$Kind,

  [Parameter(Mandatory=$true)]
  [string]$Body,

  [string]$Url = 'http://localhost:3100/api/messages'
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $Root '.env'

if (Test-Path $EnvFile) {
  Get-Content $EnvFile | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
    $Name, $Value = $_ -split '=', 2
    [Environment]::SetEnvironmentVariable($Name.Trim(), $Value.Trim(), 'Process')
  }
}

$Headers = @{}
if ($Speaker -ne 'user') {
  if (!$env:ADMIN_SECRET) {
    throw 'ADMIN_SECRET is required for claude/codex messages. Run scripts\start-agent-room.ps1 once to create .env.'
  }
  $Headers['x-admin-secret'] = $env:ADMIN_SECRET
}

$Payload = @{
  speaker = $Speaker
  kind = $Kind
  body = $Body
} | ConvertTo-Json -Compress

Invoke-RestMethod -Uri $Url -Method Post -ContentType 'application/json; charset=utf-8' -Headers $Headers -Body $Payload | Out-Null
Write-Host "Posted $Speaker/$Kind message."
