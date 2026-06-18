param(
    [string]$SessionId,
    [ValidateSet("moonbridge", "gpt-5.5")]
    [string]$TargetModel = "moonbridge",
    [string]$Prompt = "Provider inheritance smoke test. Reply with one concise sentence and do not modify files.",
    [int]$TimeoutSeconds = 90
)

. (Join-Path (Split-Path -Parent (Split-Path -Parent $PSCommandPath)) "config\paths.ps1")

if (-not $SessionId) {
    $native = Get-ChildItem -Recurse -File -LiteralPath (Join-Path $CodexHome "sessions") -Filter "*.jsonl" |
        Sort-Object LastWriteTime -Descending |
        Where-Object {
            try {
                $first = Get-Content -LiteralPath $_.FullName -TotalCount 1 | ConvertFrom-Json
                $first.payload.model_provider -eq "openai"
            }
            catch { $false }
        } |
        Select-Object -First 1
    if (-not $native) { throw "No native/openai Codex session files found." }
    $first = Get-Content -LiteralPath $native.FullName -TotalCount 1 | ConvertFrom-Json
    $SessionId = $first.payload.id
}

$resultDir = Join-Path $StackRoot "runtime\logs"
New-Item -ItemType Directory -Force -Path $resultDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
$resultPath = Join-Path $resultDir "codex-thread-provider-test-$stamp.txt"

function Invoke-CodexBounded {
    param(
        [string]$Name,
        [object[]]$ArgumentArray,
        [int]$Seconds
    )
    $outPath = Join-Path $resultDir "codex-thread-provider-test-$stamp-$Name.out.log"
    $errPath = Join-Path $resultDir "codex-thread-provider-test-$stamp-$Name.err.log"
    $cleanArgs = @($ArgumentArray | Where-Object { $null -ne $_ -and $_ -ne "" } | ForEach-Object { [string]$_ })
    try {
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
    }
    catch {
        $_.Exception.Message | Set-Content -LiteralPath $errPath -Encoding UTF8
        return [pscustomobject]@{
            Test = $Name
            ExitCode = $null
            Success = $false
            TimedOut = $false
            OutLog = $outPath
            ErrLog = $errPath
        }
    }
    $exited = $proc.WaitForExit($Seconds * 1000)
    if ($exited) {
        $proc.WaitForExit()
        $proc.StandardOutput.ReadToEnd() | Set-Content -LiteralPath $outPath -Encoding UTF8
        $proc.StandardError.ReadToEnd() | Set-Content -LiteralPath $errPath -Encoding UTF8
    }
    if (-not $exited) {
        try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}
        $proc.StandardOutput.ReadToEnd() | Set-Content -LiteralPath $outPath -Encoding UTF8
        $proc.StandardError.ReadToEnd() | Set-Content -LiteralPath $errPath -Encoding UTF8
        return [pscustomobject]@{
            Test = $Name
            ExitCode = $null
            Success = $false
            TimedOut = $true
            OutLog = $outPath
            ErrLog = $errPath
        }
    }
    return [pscustomobject]@{
        Test = $Name
        ExitCode = $proc.ExitCode
        Success = ($proc.ExitCode -eq 0)
        TimedOut = $false
        OutLog = $outPath
        ErrLog = $errPath
    }
}

function ConvertTo-ProcessArgument {
    param([string]$Value)
    if ($Value -notmatch '[\s"]') {
        return $Value
    }
    return '"' + ($Value -replace '"', '\"') + '"'
}

$tests = @(
    @{
        Name = "exec-resume-model"
        Args = @("exec", "resume", $SessionId, "-m", $TargetModel, "--skip-git-repo-check", $Prompt)
    },
    @{
        Name = "fork-model"
        Args = @("fork", $SessionId, "-m", $TargetModel, "--no-alt-screen", $Prompt)
    },
    @{
        Name = "exec-resume-config"
        Args = @("exec", "resume", $SessionId, "-c", "model=`"$TargetModel`"", "-c", "model_provider=`"moonbridge`"", "--skip-git-repo-check", $Prompt)
    },
    @{
        Name = "fork-config"
        Args = @("fork", $SessionId, "-c", "model=`"$TargetModel`"", "-c", "model_provider=`"moonbridge`"", "--no-alt-screen", $Prompt)
    }
)

"SessionId: $SessionId" | Set-Content -LiteralPath $resultPath -Encoding UTF8
"TargetModel: $TargetModel" | Add-Content -LiteralPath $resultPath -Encoding UTF8
"TimeoutSeconds: $TimeoutSeconds" | Add-Content -LiteralPath $resultPath -Encoding UTF8

$summary = @()
foreach ($test in $tests) {
    "--- $($test.Name) ---" | Add-Content -LiteralPath $resultPath -Encoding UTF8
    "Args: $($test.Args -join ' ')" | Add-Content -LiteralPath $resultPath -Encoding UTF8
    $result = Invoke-CodexBounded -Name $test.Name -ArgumentArray $test.Args -Seconds $TimeoutSeconds
    $summary += $result
    $result | Format-List | Out-String | Add-Content -LiteralPath $resultPath -Encoding UTF8
}

$summary | Format-Table -AutoSize
Write-Host "Result log: $resultPath"
