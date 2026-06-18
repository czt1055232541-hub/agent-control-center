$StackRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = "E:\Python\python.exe"
Push-Location -LiteralPath $StackRoot
try {
    $env:PYTHONPATH = Join-Path $StackRoot "src"
    & $PythonExe -m feishu_stack.cli status-control-center
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
