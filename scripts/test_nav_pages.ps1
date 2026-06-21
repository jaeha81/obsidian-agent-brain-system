$docsRoot = "G:\내 드라이브\obsidian-agent-brain-system\docs"
$pages = @(
    @{path="repo\index.html";             label="레포대시보드"},
    @{path="wishket\index.html";          label="위시켓"},
    @{path="daily-plus\index.html";       label="오늘의플러스"},
    @{path="task-board\index.html";       label="태스크보드"},
    @{path="claude-code\index.html";      label="Claude앱"},
    @{path="codex\index.html";            label="Codex"},
    @{path="chris\index.html";            label="Chris"},
    @{path="charlie\index.html";          label="Charlie"},
    @{path="my-dev\index.html";           label="내소개"},
    @{path="shorts\index.html";           label="쇼츠"},
    @{path="chsh-mining\index.html";      label="CHSH마이닝"},
    @{path="threads\index.html";          label="쓰레드자동화"},
    @{path="kmong\index.html";            label="크몽"},
    @{path="workflow\index.html";         label="워크플로우"},
    @{path="ai-usage.html";               label="AI사용량"},
    @{path="wiki-gate.html";              label="Wiki Gate"},
    @{path="bucky-agent-os.html";         label="BuckyOS"}
)
Write-Host ("{0,-14} {1,-8} {2,-8} {3}" -f "라벨","auth","nav.js","결과")
Write-Host ("-" * 45)
$allOk = $true
foreach ($p in $pages) {
    $content = Get-Content "$docsRoot\$($p.path)" -Raw -ErrorAction SilentlyContinue
    $hasAuth = if ($content -match "bucky_auth|auth\.js") { "OK" } else { "MISS" }
    $hasNav  = if ($content -match "nav\.js") { "OK" } else { "MISS" }
    $ok = ($hasAuth -eq "OK" -and $hasNav -eq "OK")
    if (-not $ok) { $allOk = $false }
    $result = if ($ok) { "PASS" } else { "FAIL" }
    $color  = if ($ok) { "Green" } else { "Red" }
    Write-Host ("{0,-14} {1,-8} {2,-8} {3}" -f $p.label,$hasAuth,$hasNav,$result) -ForegroundColor $color
}
Write-Host ("-" * 45)
$finalMsg = if ($allOk) { "전체: ALL PASS" } else { "전체: FAIL 있음" }
$finalColor = if ($allOk) { "Green" } else { "Red" }
Write-Host $finalMsg -ForegroundColor $finalColor
