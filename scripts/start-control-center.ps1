param(
    [switch]$NoOpen,
    [switch]$NoBuild,
    [switch]$NoPause
)

$StackRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = if ($env:PYTHON_EXE) { $env:PYTHON_EXE } else { "python" }
$argsList = @("-m", "feishu_stack.cli", "serve-control-center")
if (-not $NoOpen) { $argsList += "--open" }
if ($NoBuild) { $argsList += "--no-build" }
Push-Location -LiteralPath $StackRoot
try {
    $env:PYTHONPATH = Join-Path $StackRoot "src"
    & $PythonExe @argsList
    $code = $LASTEXITCODE
}
finally {
    Pop-Location
}
if (-not $NoPause) { Read-Host "Press Enter to close" | Out-Null }
exit $code
