. (Join-Path (Split-Path -Parent $PSScriptRoot) "config\paths.ps1")

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

$config = if (Test-Path -LiteralPath $CodexConfig) { Get-Content -Raw -LiteralPath $CodexConfig } else { "" }
$model = if ($config -match '(?m)^model\s*=\s*"([^"]+)"') { $Matches[1] } else { "unknown" }
$provider = if ($config -match '(?m)^model_provider\s*=\s*"([^"]+)"') { $Matches[1] } else { "openai/default" }

[pscustomobject]@{
    CodexModel = $model
    CodexProvider = $provider
    OpenClawPort = if (Test-Port $OpenClawPort) { "listening" } else { "closed" }
    MoonBridgePort = if (Test-Port $MoonPort) { "listening" } else { "closed" }
    OpenClawPid = Get-PidStatus $PidOpenClaw
    MoonBridgePid = Get-PidStatus $PidMoon
    CodexAgentPid = Get-PidStatus $PidCodex
    CodexHome = $CodexHome
    StackRoot = $StackRoot
} | Format-List
