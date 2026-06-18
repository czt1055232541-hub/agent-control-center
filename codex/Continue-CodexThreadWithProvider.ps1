param(
    [Parameter(Mandatory=$true)]
    [string]$SessionId,
    [ValidateSet("moonbridge", "gpt-5.5")]
    [string]$TargetModel = "moonbridge",
    [string]$Prompt = "Continue this conversation with the selected provider.",
    [int]$TimeoutSeconds = 300
)

. (Join-Path (Split-Path -Parent (Split-Path -Parent $PSCommandPath)) "config\paths.ps1")

function ConvertTo-ProcessArgument {
    param([string]$Value)
    if ($Value -notmatch '[\s"]') {
        return $Value
    }
    return '"' + ($Value -replace '"', '\"') + '"'
}

function Invoke-CodexBounded {
    param(
        [string]$Name,
        [object[]]$ArgumentArray
    )
    $resultDir = Join-Path $StackRoot "runtime\logs"
    New-Item -ItemType Directory -Force -Path $resultDir | Out-Null
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
    $outPath = Join-Path $resultDir "codex-continue-$stamp-$Name.out.log"
    $errPath = Join-Path $resultDir "codex-continue-$stamp-$Name.err.log"
    $cleanArgs = @($ArgumentArray | Where-Object { $null -ne $_ -and $_ -ne "" } | ForEach-Object { [string]$_ })
    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $CodexBin
    $psi.Arguments = ($cleanArgs | ForEach-Object { ConvertTo-ProcessArgument $_ }) -join " "
    $psi.WorkingDirectory = $StackRoot
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $proc = [System.Diagnostics.Process]::new()
    $proc.StartInfo = $psi
    [void]$proc.Start()
    $exited = $proc.WaitForExit($TimeoutSeconds * 1000)
    if ($exited) {
        $proc.WaitForExit()
        $proc.StandardOutput.ReadToEnd() | Set-Content -LiteralPath $outPath -Encoding UTF8
        $proc.StandardError.ReadToEnd() | Set-Content -LiteralPath $errPath -Encoding UTF8
        return [pscustomobject]@{ ExitCode = $proc.ExitCode; TimedOut = $false; OutLog = $outPath; ErrLog = $errPath }
    }
    try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}
    $proc.StandardOutput.ReadToEnd() | Set-Content -LiteralPath $outPath -Encoding UTF8
    $proc.StandardError.ReadToEnd() | Set-Content -LiteralPath $errPath -Encoding UTF8
    return [pscustomobject]@{ ExitCode = $null; TimedOut = $true; OutLog = $outPath; ErrLog = $errPath }
}

Write-Host "Trying direct exec resume with target model $TargetModel ..."
$direct = Invoke-CodexBounded -Name "direct-resume" -ArgumentArray @("exec", "resume", $SessionId, "-m", $TargetModel, "--skip-git-repo-check", $Prompt)
$direct | Format-List
if ($direct.ExitCode -eq 0) {
    exit 0
}

Write-Host "Direct exec resume failed or timed out. Falling back to summary migration."
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

$fallback = Invoke-CodexBounded -Name "summary-migration" -ArgumentArray @("exec", "-m", $TargetModel, "--skip-git-repo-check", $migrationPrompt)
$fallback | Format-List
if ($fallback.ExitCode -eq 0) {
    exit 0
}
exit 1
