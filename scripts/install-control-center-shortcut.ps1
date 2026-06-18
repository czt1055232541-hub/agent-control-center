param([switch]$NoPause)

$StackRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = "E:\Python\python.exe"
Push-Location -LiteralPath (Join-Path $StackRoot "control-center")
try {
    & $PythonExe -m feishu_stack.cli install-shortcut
    $code = $LASTEXITCODE
}
finally {
    Pop-Location
}
if (-not $NoPause) { Read-Host "Press Enter to close" | Out-Null }
exit $code
