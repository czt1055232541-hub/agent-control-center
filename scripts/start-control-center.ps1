param(
    [switch]$NoOpen,
    [switch]$NoBuild,
    [switch]$NoPause
)

$ErrorActionPreference = "Stop"
. (Join-Path (Split-Path -Parent $PSScriptRoot) "config\paths.ps1")

$PythonExe = "E:\Python\python.exe"
$ControlCenterDir = Join-Path $StackRoot "control-center"
$WebDir = Join-Path $ControlCenterDir "web"
$WebDistIndex = Join-Path $WebDir "dist\index.html"
$ApiPort = 8765
$ApiUrl = "http://127.0.0.1:$ApiPort"
$PidControlCenter = Join-Path $PidDir "control-center-api.pid"
$ApiOutLog = Join-Path $LogDir "control-center-api-out.log"
$ApiErrLog = Join-Path $LogDir "control-center-api-err.log"

function Test-Port {
    param([int]$Port)
    $client = $null
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        $ok = $async.AsyncWaitHandle.WaitOne(500, $false)
        if ($ok) {
            $client.EndConnect($async)
            $client.Close()
            return $true
        }
        $client.Close()
        return $false
    }
    catch {
        if ($client -ne $null) { $client.Close() }
        return $false
    }
}

function Wait-Port {
    param([int]$Port, [int]$Seconds = 30)
    for ($i = 1; $i -le $Seconds; $i++) {
        if (Test-Port -Port $Port) { return $true }
        Start-Sleep -Seconds 1
    }
    return (Test-Port -Port $Port)
}

function Pause-IfNeeded {
    if (-not $NoPause) { Read-Host "Press Enter to close" | Out-Null }
}

New-Item -ItemType Directory -Force -Path $RuntimeDir, $LogDir, $PidDir | Out-Null

if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw "Python not found: $PythonExe"
}

Push-Location -LiteralPath $ControlCenterDir
try {
    & $PythonExe -c "import feishu_stack, fastapi, uvicorn" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installing Python control package ..."
        & $PythonExe -m pip install -e ".[dev]"
        if ($LASTEXITCODE -ne 0) { throw "Python package install failed." }
    }
}
finally {
    Pop-Location
}

if (-not $NoBuild -and -not (Test-Path -LiteralPath $WebDistIndex)) {
    Write-Host "Building Control Center web UI ..."
    Push-Location -LiteralPath $WebDir
    try {
        npm install
        if ($LASTEXITCODE -ne 0) { throw "npm install failed." }
        npm run build
        if ($LASTEXITCODE -ne 0) { throw "npm run build failed." }
    }
    finally {
        Pop-Location
    }
}

if (-not (Test-Port -Port $ApiPort)) {
    Write-Host "Starting Control Center API on $ApiUrl ..."
    $proc = Start-Process -FilePath $PythonExe `
        -ArgumentList "-m", "uvicorn", "feishu_stack.app:app", "--host", "127.0.0.1", "--port", "$ApiPort" `
        -WorkingDirectory $ControlCenterDir `
        -WindowStyle Hidden `
        -RedirectStandardOutput $ApiOutLog `
        -RedirectStandardError $ApiErrLog `
        -PassThru
    Set-Content -LiteralPath $PidControlCenter -Value $proc.Id -Encoding ASCII
    if (-not (Wait-Port -Port $ApiPort -Seconds 30)) {
        throw "Control Center API did not become ready. See $ApiErrLog"
    }
}
else {
    Write-Host "Control Center API is already listening on $ApiUrl."
}

if (-not $NoOpen) {
    Start-Process $ApiUrl | Out-Null
}

Write-Host "Control Center: $ApiUrl"
Write-Host "Logs: $LogDir"
Pause-IfNeeded
