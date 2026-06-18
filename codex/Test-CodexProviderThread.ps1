param(
    [string]$SessionId,
    [ValidateSet("moonbridge", "gpt-5.5")]
    [string]$TargetModel = "moonbridge",
    [string]$Prompt = "Provider inheritance smoke test. Reply with one concise sentence and do not modify files."
)

. (Join-Path (Split-Path -Parent (Split-Path -Parent $PSCommandPath)) "config\paths.ps1")

if (-not $SessionId) {
    $latest = Get-ChildItem -Recurse -File -LiteralPath (Join-Path $CodexHome "sessions") -Filter "*.jsonl" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $latest) { throw "No Codex session files found." }
    $first = Get-Content -LiteralPath $latest.FullName -TotalCount 1 | ConvertFrom-Json
    $SessionId = $first.payload.id
}

$resultDir = Join-Path $StackRoot "runtime\logs"
New-Item -ItemType Directory -Force -Path $resultDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$resultPath = Join-Path $resultDir "codex-thread-provider-test-$stamp.txt"

$tests = @(
    @{
        Name = "resume-model"
        Args = @("resume", $SessionId, "-m", $TargetModel, "--no-alt-screen", $Prompt)
    },
    @{
        Name = "fork-model"
        Args = @("fork", $SessionId, "-m", $TargetModel, "--no-alt-screen", $Prompt)
    },
    @{
        Name = "fork-config"
        Args = @("fork", $SessionId, "-c", "model=`"$TargetModel`"", "-c", "model_provider=`"moonbridge`"", "--no-alt-screen", $Prompt)
    }
)

"SessionId: $SessionId" | Set-Content -LiteralPath $resultPath -Encoding UTF8
"TargetModel: $TargetModel" | Add-Content -LiteralPath $resultPath -Encoding UTF8

$summary = @()
foreach ($test in $tests) {
    "--- $($test.Name) ---" | Add-Content -LiteralPath $resultPath -Encoding UTF8
    $output = & $CodexBin @($test.Args) 2>&1
    $code = $LASTEXITCODE
    $output | Add-Content -LiteralPath $resultPath -Encoding UTF8
    $summary += [pscustomobject]@{
        Test = $test.Name
        ExitCode = $code
        Success = ($code -eq 0)
    }
}

$summary | Format-Table -AutoSize
Write-Host "Result log: $resultPath"
