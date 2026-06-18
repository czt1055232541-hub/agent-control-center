param([switch]$NoPause)

$StackRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = "E:\Python\python.exe"
Push-Location -LiteralPath $StackRoot
try {
    $env:PYTHONPATH = Join-Path $StackRoot "src"
    & $PythonExe -m feishu_stack.cli stack stop
    $code = $LASTEXITCODE
}
finally {
    Pop-Location
}
if (-not $NoPause) { Read-Host "Press Enter to close" | Out-Null }
exit $code
