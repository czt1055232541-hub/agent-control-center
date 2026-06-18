param(
    [ValidateSet("native", "moonbridge", "current")]
    [string]$CodexMode = "current",
    [switch]$NoPause
)

$PythonExe = "E:\Python\python.exe"
$ControlCenterDir = "F:\1AI\Agent control center"

Push-Location -LiteralPath $ControlCenterDir
try {
    $mode = $CodexMode
    if ($mode -eq "current") {
        $statusJson = & $PythonExe -m feishu_stack.cli status --json
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        $status = $statusJson | ConvertFrom-Json
        $mode = $status.codex.mode
    }
    $action = if ($mode -eq "moonbridge") { "start-moonbridge" } else { "start-native" }
    & $PythonExe -m feishu_stack.cli stack $action
    $code = $LASTEXITCODE
}
finally {
    Pop-Location
}

if (-not $NoPause) { Read-Host "Press Enter to close" | Out-Null }
exit $code
