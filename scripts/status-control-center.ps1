$StackRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = if ($env:PYTHON_EXE) { $env:PYTHON_EXE } else { "python" }
Push-Location -LiteralPath $StackRoot
try {
    $env:PYTHONPATH = Join-Path $StackRoot "src"
    & $PythonExe -m feishu_stack.cli status-control-center
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
