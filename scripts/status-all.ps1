$StackRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = "E:\Python\python.exe"
Push-Location -LiteralPath (Join-Path $StackRoot "control-center")
try {
    & $PythonExe -m feishu_stack.cli status
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
