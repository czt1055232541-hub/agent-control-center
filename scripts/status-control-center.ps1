. (Join-Path (Split-Path -Parent $PSScriptRoot) "config\paths.ps1")

$ApiPort = 8765
$PidControlCenter = Join-Path $PidDir "control-center-api.pid"
$WebDistIndex = Join-Path $StackRoot "control-center\web\dist\index.html"
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

function Get-PidStatus {
    param([string]$PidFile)
    if (-not (Test-Path -LiteralPath $PidFile)) { return "no pid" }
    try {
        $pidText = Get-Content -LiteralPath $PidFile | Select-Object -First 1
        $proc = Get-Process -Id ([int]$pidText) -ErrorAction SilentlyContinue
        if ($proc) { return "pid $pidText running ($($proc.ProcessName))" }
        return "pid $pidText not running"
    }
    catch { return "invalid pid file" }
}

[pscustomobject]@{
    Url = "http://127.0.0.1:$ApiPort"
    ApiPort = if (Test-Port $ApiPort) { "listening" } else { "closed" }
    ApiPid = Get-PidStatus $PidControlCenter
    GuiBuild = if (Test-Path -LiteralPath $WebDistIndex) { "present" } else { "missing" }
    StdoutLog = $ApiOutLog
    StderrLog = $ApiErrLog
} | Format-List
