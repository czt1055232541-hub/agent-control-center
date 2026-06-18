$PythonExe = "E:\Python\python.exe"
Push-Location -LiteralPath "F:\1AI\Agent control center"
try {
    & $PythonExe -m feishu_stack.cli status
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
