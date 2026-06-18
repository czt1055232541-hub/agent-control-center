param([int]$Keep = 1)

$StackRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$PythonExe = "E:\Python\python.exe"
Push-Location -LiteralPath (Join-Path $StackRoot "control-center")
try {
    & $PythonExe -m feishu_stack.cli backups clean
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
