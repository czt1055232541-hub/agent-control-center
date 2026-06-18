param([switch]$NoPause)

$ErrorActionPreference = "Continue"
. (Join-Path (Split-Path -Parent $PSScriptRoot) "config\paths.ps1")

function Write-Section {
    param([string]$Text)
    Write-Host ""
    Write-Host "============================================================"
    Write-Host $Text
    Write-Host "============================================================"
}

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

function Stop-ByPidFile {
    param([string]$PidFile, [string]$Name)
    if (-not (Test-Path -LiteralPath $PidFile)) {
        Write-Host "$Name PID file not found: $PidFile"
        return
    }
    try {
        $pidText = Get-Content -LiteralPath $PidFile -ErrorAction Stop | Select-Object -First 1
        if ([string]::IsNullOrWhiteSpace($pidText)) {
            Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
            return
        }
        $proc = Get-Process -Id ([int]$pidText) -ErrorAction SilentlyContinue
        if ($proc -ne $null) {
            Write-Host "Stopping $Name. PID: $pidText Process: $($proc.ProcessName)"
            Stop-Process -Id ([int]$pidText) -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        }
        Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
    }
    catch {
        Write-Host "Failed to stop $Name by PID file: $($_.Exception.Message)"
    }
}

function Stop-ByPort {
    param([int]$Port, [string]$Name)
    $lines = netstat -ano | Select-String ":$Port"
    $pids = @()
    foreach ($line in $lines) {
        $text = $line.ToString().Trim()
        if ($text -match "LISTENING\s+(\d+)$") { $pids += [int]$matches[1] }
    }
    foreach ($pidValue in ($pids | Select-Object -Unique)) {
        $proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
        if ($proc -ne $null) {
            Write-Host "Stopping $Name by port $Port. PID: $pidValue Process: $($proc.ProcessName)"
            Stop-Process -Id $pidValue -Force -ErrorAction SilentlyContinue
        }
    }
}

function Stop-CodexAgentFallback {
    try {
        $agentRootRegex = [regex]::Escape($CodexAgentDir)
        $nodeProcs = Get-CimInstance Win32_Process |
            Where-Object { $_.Name -match "node.exe" -and $_.CommandLine -match "dist\\src\\index.js" -and $_.CommandLine -match $agentRootRegex }
        foreach ($p in $nodeProcs) {
            Write-Host "Stopping Codex Feishu Agent node process. PID: $($p.ProcessId)"
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        }
    }
    catch {
        Write-Host "Could not scan node processes."
    }
}

Write-Section "Stop Codex Feishu Agent"
Stop-ByPidFile -PidFile $PidCodex -Name "Codex Feishu Agent"
Stop-CodexAgentFallback

Write-Section "Stop MoonBridge"
Stop-ByPidFile -PidFile $PidMoon -Name "MoonBridge"
if (Test-Port -Port $MoonPort) { Stop-ByPort -Port $MoonPort -Name "MoonBridge" }
else { Write-Host "MoonBridge is not listening on port $MoonPort." }

Write-Section "Stop OpenClaw Gateway"
$env:OPENCLAW_HOME = $OpenClawHome
try { openclaw.cmd gateway stop } catch { Write-Host "openclaw.cmd gateway stop failed or is unavailable." }
Start-Sleep -Seconds 2
Stop-ByPidFile -PidFile $PidOpenClaw -Name "OpenClaw Gateway"
if (Test-Port -Port $OpenClawPort) { Stop-ByPort -Port $OpenClawPort -Name "OpenClaw Gateway" }
else { Write-Host "OpenClaw Gateway is not listening on port $OpenClawPort." }

Write-Section "Final status"
$gatewayReady = Test-Port -Port $OpenClawPort
$moonReady = Test-Port -Port $MoonPort
$agentAlive = $false
if (Test-Path -LiteralPath $PidCodex) {
    try {
        $pidText = Get-Content -LiteralPath $PidCodex | Select-Object -First 1
        $agentAlive = ((Get-Process -Id ([int]$pidText) -ErrorAction SilentlyContinue) -ne $null)
    }
    catch { $agentAlive = $false }
}
Write-Host "OpenClaw Gateway : $(if ($gatewayReady) { 'STILL RUNNING' } else { 'STOPPED' })"
Write-Host "MoonBridge        : $(if ($moonReady) { 'STILL RUNNING' } else { 'STOPPED' })"
Write-Host "Codex Agent       : $(if ($agentAlive) { 'STILL RUNNING' } else { 'STOPPED' })"
Write-Host "Codex Desktop and interactive codex.exe processes are intentionally not stopped."

if (-not $NoPause) { Read-Host "Press Enter to close" }
if ($moonReady -or $agentAlive) { exit 1 }
exit 0
