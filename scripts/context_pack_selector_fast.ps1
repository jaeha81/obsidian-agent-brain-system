param(
    [string]$Project = "",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Body
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false

$request = ($Body -join " ").Trim()
if (-not $Project) {
    $Project = (Get-Location).Path
}

$directPacks = @(
    "ObsidianVault/06_Context_Packs/bucky-context-efficiency-goal-mode.md",
    "ObsidianVault/06_Context_Packs/bucky-user-communication-output-policy.md"
)

$governancePacks = $directPacks + @(
    "ObsidianVault/03_Projects/agents/codex-instructions.md",
    "ObsidianVault/03_Projects/agents/roles.md",
    "ObsidianVault/03_Projects/agents/bucky.md"
)

function Test-AnyTrigger {
    param(
        [string]$Text,
        [string[]]$Triggers
    )

    foreach ($trigger in $Triggers) {
        if ($Text.IndexOf($trigger, [StringComparison]::OrdinalIgnoreCase) -ge 0) {
            return $true
        }
    }
    return $false
}

$directTriggers = @(
    "git status",
    "unittest",
    "py_compile",
    "syntax",
    "test",
    "changed files",
    "selected tests",
    "commit/push",
    "do not commit",
    "do not push",
    "kmong"
)

$governanceTriggers = @(
    "context waste",
    "instruction",
    "governance",
    "operation",
    "usage",
    "slow",
    "codex",
    "bucky",
    "claude",
    "wiki",
    "graph",
    "graphify"
)

if (Test-AnyTrigger -Text $request -Triggers $governanceTriggers) {
    $key = "instruction_governance"
    $agent = "Bucky Instruction Auditor"
    $role = "instruction governance / operating-system repair"
    $packs = $governancePacks
    $notes = @(
        "Use for diagnosing excessive instructions, role conflicts, context waste, and Bucky/Codex/Claude operating rules.",
        "Prefer a short root-cause finding and a minimal rule/script patch over broad Vault exploration."
    )
} else {
    $key = "direct_execution"
    $agent = "Codex Direct Executor"
    $role = "narrow execution / focused verification"
    $packs = $directPacks
    $notes = @(
        "Use when the user already provides files, commands, execution order, or forbidden actions.",
        "Run the requested first command before reading plans, broad diffs, whole files, or extra context.",
        "Open only failing files/lines after verification fails."
    )
}

$packet = [ordered]@{
    project = $Project
    agent = $agent
    role = $role
    key = $key
    goal = $(if ($request) { $request } else { "Handle the requested task inside the current project scope." })
    scope = "Use only the current project and Bucky-selected references unless the user expands scope."
    constraints = @(
        "Do not reuse another repo/folder instruction packet automatically.",
        "Do not commit, push, delete, move, reset, or run non-dry-run legacy migration without explicit user approval.",
        "Preserve user changes and report blockers with evidence.",
        "Keep context compact; use referenced files instead of pasting long source material.",
        "If the user provided commands or files, run the first requested command before reading extra context."
    )
    context_packs = $packs
    references = $packs
    notes = $notes
    verification = @(
        "Run the narrow command or inspection that proves this task's done_when.",
        "For direct execution, do not broaden scope before the first requested command.",
        "For instruction governance, verify selector output and changed instruction files."
    )
    done_when = "The requested outcome is verified with current files, command output, or saved evidence."
    fallback = "If Bucky is unavailable or the packet is too broad, apply the direct execution gate and ask for a narrower packet."
}

$packet | ConvertTo-Json -Depth 6
