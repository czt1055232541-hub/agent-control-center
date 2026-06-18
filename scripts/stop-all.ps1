param([switch]$NoPause)

$PythonExe = "E:\Python\python.exe"
Push-Location -LiteralPath "F:\1AI\Agent control center"
try {
    & $PythonExe -m feishu_stack.cli stack stop
    $code = $LASTEXITCODE
}
finally {
    Pop-Location
}
if (-not $NoPause) { Read-Host "Press Enter to close" | Out-Null }
exit $code
