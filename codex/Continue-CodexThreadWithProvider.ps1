param(
    [Parameter(Mandatory=$true)]
    [string]$SessionId,
    [ValidateSet("moonbridge", "gpt-5.5")]
    [string]$TargetModel = "moonbridge",
    [string]$Prompt = "Continue this conversation with the selected provider."
)

. (Join-Path (Split-Path -Parent (Split-Path -Parent $PSCommandPath)) "config\paths.ps1")

$testScript = Join-Path $PSScriptRoot "Test-CodexProviderThread.ps1"
Write-Host "Trying direct fork with target model $TargetModel ..."
& $CodexBin fork $SessionId -m $TargetModel --no-alt-screen $Prompt
if ($LASTEXITCODE -eq 0) {
    exit 0
}

Write-Host "Direct fork failed. Falling back to summary migration."
$sessionFile = Get-ChildItem -Recurse -File -LiteralPath (Join-Path $CodexHome "sessions") -Filter "*.jsonl" |
    Where-Object {
        try {
            $first = Get-Content -LiteralPath $_.FullName -TotalCount 1 | ConvertFrom-Json
            $first.payload.id -eq $SessionId
        }
        catch { $false }
    } |
    Select-Object -First 1

if (-not $sessionFile) {
    throw "Session file not found for $SessionId"
}

$lines = Get-Content -LiteralPath $sessionFile.FullName
$tail = $lines | Select-Object -Last 80
$migrationPrompt = @"
Continue a prior Codex conversation using a migrated summary.

Prior session id: $SessionId
Source rollout tail follows. Summarize the relevant state internally and answer the user's request.

$($tail -join "`n")

User request:
$Prompt
"@

& $CodexBin exec -m $TargetModel --skip-git-repo-check $migrationPrompt
