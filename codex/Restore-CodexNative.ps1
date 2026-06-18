$StackRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$PythonExe = "E:\Python\python.exe"
Push-Location -LiteralPath (Join-Path $StackRoot "control-center")
try {
    & $PythonExe -m feishu_stack.cli switch-provider native
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
