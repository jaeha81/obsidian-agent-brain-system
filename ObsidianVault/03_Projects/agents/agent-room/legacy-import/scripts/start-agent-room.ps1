param(
  [int]$Port = 3100
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $Root '.env'
$ExampleFile = Join-Path $Root '.env.example'

if (!(Test-Path $EnvFile)) {
  Copy-Item $ExampleFile $EnvFile
}

$Content = Get-Content $EnvFile -Raw
if ($Content -notmatch '(?m)^ADMIN_SECRET=\S+') {
  $Bytes = New-Object byte[] 32
  $Rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  $Rng.GetBytes($Bytes)
  $Secret = [Convert]::ToBase64String($Bytes)
  if ($Content -match '(?m)^ADMIN_SECRET=') {
    $Content = $Content -replace '(?m)^ADMIN_SECRET=.*$', "ADMIN_SECRET=$Secret"
  } else {
    $Content += "`nADMIN_SECRET=$Secret`n"
  }
}
if ($Content -match '(?m)^PORT=') {
  $Content = $Content -replace '(?m)^PORT=.*$', "PORT=$Port"
} else {
  $Content += "`nPORT=$Port`n"
}
Set-Content -Encoding UTF8 $EnvFile $Content

Get-Content $EnvFile | ForEach-Object {
  if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
  $Name, $Value = $_ -split '=', 2
  [Environment]::SetEnvironmentVariable($Name.Trim(), $Value.Trim(), 'Process')
}

$env:PORT = [string]$Port
Set-Location $Root
node server.js
