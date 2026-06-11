param(
  [string]$Date = (Get-Date -Format 'yyyy-MM-dd'),
  [string]$Author = 'Codex'
)

$ErrorActionPreference = 'Stop'
$DriveName = -join @([char]0xB0B4, ' ', [char]0xB4DC, [char]0xB77C, [char]0xC774, [char]0xBE0C)
$Shared = Join-Path (Join-Path 'G:\' $DriveName) 'JH-SHARED'
$DailyRoot = Join-Path $Shared '04_DAILY_REPORTS'

$Year = $Date.Substring(0, 4)
$Month = $Date.Substring(0, 7)
$TargetDir = Join-Path (Join-Path $DailyRoot $Year) $Month
$EntriesDir = Join-Path $TargetDir "$Date.entries"
$Target = Join-Path $TargetDir "$Date.md"

New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null

$Entries = @()
if (Test-Path $EntriesDir) {
  $Files = Get-ChildItem -Path $EntriesDir -Recurse -Filter '*.jsonl' -File
  foreach ($File in $Files) {
    $Lines = Get-Content -Encoding UTF8 $File.FullName
    foreach ($Line in $Lines) {
      if ([string]::IsNullOrWhiteSpace($Line)) {
        continue
      }
      try {
        $Entry = $Line | ConvertFrom-Json
        $Entries += $Entry
      } catch {
        Write-Warning "Skipped invalid JSONL line in $($File.FullName)"
      }
    }
  }
}

$Entries = $Entries | Sort-Object createdAt, speaker, id

function Format-EntryList {
  param(
    [object[]]$Items,
    [string]$EmptyText = '-'
  )

  if (!$Items -or $Items.Count -eq 0) {
    return $EmptyText
  }

  $Lines = foreach ($Item in $Items) {
    $Stamp = ''
    if ($Item.createdAt) {
      $Stamp = ([datetime]$Item.createdAt).ToLocalTime().ToString('HH:mm')
    }
    "- [$($Item.speaker)@$($Item.host) $Stamp] $($Item.body)"
  }
  return ($Lines -join "`r`n")
}

function Format-IssueTable {
  param([object[]]$Items)

  $Header = "| 우선순위 | 이슈 | 상태 | 처리 | 작성자 |`r`n|---|---|---|---|---|"
  if (!$Items -or $Items.Count -eq 0) {
    return "$Header`r`n|  |  |  |  |  |"
  }

  $Rows = foreach ($Item in $Items) {
    $Priority = if ($Item.priority) { $Item.priority } else { '-' }
    $Status = if ($Item.status) { $Item.status } else { '-' }
    "| $Priority | $($Item.body) | $Status | - | $($Item.speaker)@$($Item.host) |"
  }

  return "$Header`r`n$($Rows -join "`r`n")"
}

$Summary = @($Entries | Where-Object { $_.kind -eq 'summary' })
$Changes = @($Entries | Where-Object { $_.kind -eq 'change' })
$Issues = @($Entries | Where-Object { $_.kind -eq 'issue' })
$Verification = @($Entries | Where-Object { $_.kind -eq 'verification' })
$Remaining = @($Entries | Where-Object { $_.kind -eq 'remaining' })
$Handoff = @($Entries | Where-Object { $_.kind -eq 'handoff' })
$NextCheck = @($Entries | Where-Object { $_.kind -eq 'next-check' })
$Notes = @($Entries | Where-Object { $_.kind -eq 'note' })

$Content = @"
# 일일보고 — $Date

> 대상: 사용자 · Claude · Codex  
> 기준 시스템: JH Agent Room / JH-SHARED  
> 작성자: $Author  
> 생성 방식: append-only entries JSONL에서 재생성

## 1. 오늘 작업 요약

$(Format-EntryList -Items $Summary)

## 2. 완료된 변경

$(Format-EntryList -Items $Changes)

## 3. 주요 이슈 및 처리 상태

$(Format-IssueTable -Items $Issues)

## 4. 검증 결과

$(Format-EntryList -Items $Verification)

## 5. 남은 작업

$(Format-EntryList -Items $Remaining)

## 6. Claude에게 전달할 내용

$(Format-EntryList -Items $Handoff)

## 7. 다음 시작 시 체크

$(Format-EntryList -Items $NextCheck -EmptyText '```powershell
cd D:\ai프로젝트\JH-Agent-Room
git pull origin main
powershell -ExecutionPolicy Bypass -File .\scripts\check-agent-context.ps1
```')

## 8. 추가 메모

$(Format-EntryList -Items $Notes)

---

원본 입력 폴더:

~~~text
$EntriesDir
~~~

Claude와 Codex는 이 Markdown 파일을 동시에 직접 편집하지 않는다. 각자 `scripts\add-daily-entry.ps1`로 자기 JSONL 로그에 입력하고, 필요할 때 `scripts\build-daily-report.ps1`로 이 파일을 재생성한다.
"@

Set-Content -Encoding UTF8 $Target $Content
Write-Host "Built daily report: $Target"


