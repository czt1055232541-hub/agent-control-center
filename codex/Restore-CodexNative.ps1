$PythonExe = "E:\Python\python.exe"
Push-Location -LiteralPath "F:\1AI\Agent control center"
try {
    $env:PYTHONPATH = "F:\1AI\Agent control center\src"
    & $PythonExe -m feishu_stack.cli switch-provider native
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
