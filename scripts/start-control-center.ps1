param(
    [switch]$NoOpen,
    [switch]$NoBuild,
    [switch]$NoPause
)

$StackRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = "E:\Python\python.exe"
$argsList = @("-m", "feishu_stack.cli", "serve-control-center")
if (-not $NoOpen) { $argsList += "--open" }
if ($NoBuild) { $argsList += "--no-build" }
Push-Location -LiteralPath (Join-Path $StackRoot "control-center")
try {
    & $PythonExe @argsList
    $code = $LASTEXITCODE
}
finally {
    Pop-Location
}
if (-not $NoPause) { Read-Host "Press Enter to close" | Out-Null }
exit $code
