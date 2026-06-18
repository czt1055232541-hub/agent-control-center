param(
    [ValidateSet("native", "moonbridge", "current")]
    [string]$CodexMode = "current",
    [switch]$NoPause
)

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

function Wait-Port {
    param([int]$Port, [string]$Name, [int]$Seconds = 25)
    Write-Host "Waiting for $Name on port $Port ..."
    for ($i = 1; $i -le $Seconds; $i++) {
        if (Test-Port -Port $Port) {
            Write-Host "$Name is ready."
            return $true
        }
        Start-Sleep -Seconds 1
    }
    Write-Host "$Name is not ready after $Seconds seconds."
    return $false
}

function Ensure-File {
    param([string]$Path, [string]$Name)
    if (-not (Test-Path -LiteralPath $Path)) {
        Write-Host "$Name not found: $Path"
        return $false
    }
    return $true
}

function Ensure-Dir {
    param([string]$Path, [string]$Name)
    if (-not (Test-Path -LiteralPath $Path)) {
        Write-Host "$Name not found: $Path"
        return $false
    }
    return $true
}

function Save-Pid {
    param([string]$PidFile, [System.Diagnostics.Process]$Proc)
    try { Set-Content -LiteralPath $PidFile -Value $Proc.Id -Encoding ASCII }
    catch { Write-Host "Failed to write PID file: $PidFile" }
}

function Test-PidFileAlive {
    param([string]$PidFile)
    if (-not (Test-Path -LiteralPath $PidFile)) { return $false }
    try {
        $pidText = Get-Content -LiteralPath $PidFile -ErrorAction Stop | Select-Object -First 1
        if ([string]::IsNullOrWhiteSpace($pidText)) { return $false }
        return ((Get-Process -Id ([int]$pidText) -ErrorAction SilentlyContinue) -ne $null)
    }
    catch { return $false }
}

function Get-CurrentCodexMode {
    if (-not (Test-Path -LiteralPath $CodexConfig)) { return "native" }
    $config = Get-Content -LiteralPath $CodexConfig -Raw
    if ($config -match '(?m)^\s*model_provider\s*=\s*"moonbridge"\s*$') { return "moonbridge" }
    return "native"
}

function Build-CodexAgentIfNeeded {
    if (Test-Path -LiteralPath $CodexAgentEntry) { return $true }
    if (-not (Test-Path -LiteralPath (Join-Path $CodexAgentDir "package.json"))) {
        Write-Host "Codex Feishu Agent package.json not found: $CodexAgentDir"
        return $false
    }
    Write-Host "Codex Feishu Agent is not built. Running npm install and npm run build ..."
    Push-Location -LiteralPath $CodexAgentDir
    try {
        npm install
        if ($LASTEXITCODE -ne 0) { return $false }
        npm run build
        if ($LASTEXITCODE -ne 0) { return $false }
        return (Test-Path -LiteralPath $CodexAgentEntry)
    }
    finally {
        Pop-Location
    }
}

function Pause-IfNeeded {
    if (-not $NoPause) { Read-Host "Press Enter to close" }
}

$EffectiveCodexMode = if ($CodexMode -eq "current") { Get-CurrentCodexMode } else { $CodexMode }
$NeedMoonBridge = ($EffectiveCodexMode -eq "moonbridge")
$SwitchScript = Join-Path $StackRoot "codex\Switch-CodexProvider.ps1"

Write-Section "Preflight check"
$ok = $true
if (-not (Ensure-Dir -Path $StackRoot -Name "Stack root")) { $ok = $false }
if (-not (Ensure-Dir -Path $OpenClawHome -Name "OpenClaw home")) { $ok = $false }
if (-not (Ensure-File -Path $OpenClawGatewayCmd -Name "OpenClaw gateway script")) { $ok = $false }
if (-not (Ensure-Dir -Path $CodexHome -Name "Codex home")) { $ok = $false }
if (-not (Ensure-File -Path $CodexBin -Name "Codex executable")) { $ok = $false }
if ($CodexMode -ne "current" -and -not (Ensure-File -Path $SwitchScript -Name "Codex provider switch script")) { $ok = $false }
if (-not (Ensure-Dir -Path $CodexAgentDir -Name "Codex Feishu Agent directory")) { $ok = $false }
if (-not (Ensure-File -Path $LarkCliBin -Name "Lark CLI executable")) { $ok = $false }
if (-not (Build-CodexAgentIfNeeded)) { $ok = $false }
if ($NeedMoonBridge) {
    if (-not (Ensure-Dir -Path $MoonDir -Name "MoonBridge directory")) { $ok = $false }
    if (-not (Ensure-File -Path $MoonExe -Name "MoonBridge executable")) { $ok = $false }
    if (-not (Ensure-File -Path $MoonConfig -Name "MoonBridge config")) { $ok = $false }
}

Write-Host "StackRoot       = $StackRoot"
Write-Host "CodexHome       = $CodexHome"
Write-Host "CodexAgentDir   = $CodexAgentDir"
Write-Host "Requested mode  = $CodexMode"
Write-Host "Effective mode  = $EffectiveCodexMode"
Write-Host "Need MoonBridge = $NeedMoonBridge"

if (-not $ok) {
    Write-Host "Preflight check failed."
    Pause-IfNeeded
    exit 1
}

Write-Section "Start OpenClaw Gateway"
if (Test-Port -Port $OpenClawPort) {
    Write-Host "OpenClaw Gateway is already listening on port $OpenClawPort."
}
else {
    $openclawLaunch = "set `"OPENCLAW_HOME=$OpenClawHome`" && `"$OpenClawGatewayCmd`""
    $openclawProc = Start-Process -FilePath "cmd.exe" -ArgumentList "/d", "/c", $openclawLaunch -WorkingDirectory $OpenClawHome -WindowStyle Hidden -RedirectStandardOutput $OpenClawOutLog -RedirectStandardError $OpenClawErrLog -PassThru
    Save-Pid -PidFile $PidOpenClaw -Proc $openclawProc
    Write-Host "OpenClaw Gateway PID: $($openclawProc.Id)"
    Wait-Port -Port $OpenClawPort -Name "OpenClaw Gateway" -Seconds 25 | Out-Null
}

Write-Section "Start MoonBridge"
if (-not $NeedMoonBridge) {
    Write-Host "Codex mode is $EffectiveCodexMode. MoonBridge startup skipped."
}
elseif (Test-Port -Port $MoonPort) {
    Write-Host "MoonBridge is already listening on port $MoonPort."
}
else {
    $moonProc = Start-Process -FilePath $MoonExe -ArgumentList "-config", "`"$MoonConfig`"" -WorkingDirectory $MoonDir -WindowStyle Hidden -RedirectStandardOutput $MoonOutLog -RedirectStandardError $MoonErrLog -PassThru
    Save-Pid -PidFile $PidMoon -Proc $moonProc
    Write-Host "MoonBridge PID: $($moonProc.Id)"
    Wait-Port -Port $MoonPort -Name "MoonBridge" -Seconds 25 | Out-Null
}

Write-Section "Codex provider mode"
if ($CodexMode -eq "current") {
    Write-Host "Codex provider switch skipped. Current mode: $(Get-CurrentCodexMode)"
}
else {
    & $SwitchScript -Mode $CodexMode
    $switchOk = $?
    if (-not $switchOk) {
        Write-Host "Codex provider switch failed for mode: $CodexMode"
        Pause-IfNeeded
        exit 1
    }
}

Write-Section "Start Codex Feishu Agent"
if (Test-PidFileAlive -PidFile $PidCodex) {
    $oldPid = Get-Content -LiteralPath $PidCodex | Select-Object -First 1
    Write-Host "Codex Feishu Agent is already running. PID: $oldPid"
}
else {
    $savedEnv = @{
        CODEX_HOME = $env:CODEX_HOME
        CODEX_CLI_BIN = $env:CODEX_CLI_BIN
        AGENT_PROVIDER = $env:AGENT_PROVIDER
        AGENT_NAME = $env:AGENT_NAME
        AGENT_MENTION = $env:AGENT_MENTION
        LARK_IDENTITY = $env:LARK_IDENTITY
        LARK_CLI_OUTPUT_ENCODING = $env:LARK_CLI_OUTPUT_ENCODING
        LARK_EVENT_TIMEOUT = $env:LARK_EVENT_TIMEOUT
        LARK_CLI_BIN = $env:LARK_CLI_BIN
        LARK_CLI_CWD = $env:LARK_CLI_CWD
        OPENCLAW_HOME = $env:OPENCLAW_HOME
        CLAW_HOME = $env:CLAW_HOME
    }
    try {
        $env:CODEX_HOME = $CodexHome
        $env:CODEX_CLI_BIN = $CodexBin
        $env:AGENT_PROVIDER = "codex"
        $env:AGENT_NAME = "codex"
        $env:AGENT_MENTION = "Codex"
        $env:LARK_IDENTITY = "bot"
        $env:LARK_CLI_OUTPUT_ENCODING = "utf8"
        $env:LARK_EVENT_TIMEOUT = "8760h"
        $env:LARK_CLI_BIN = $LarkCliBin
        $env:LARK_CLI_CWD = $StackRoot
        $env:OPENCLAW_HOME = ""
        $env:CLAW_HOME = ""
        $codexProc = Start-Process -FilePath "node.exe" -ArgumentList "dist\src\index.js" -WorkingDirectory $CodexAgentDir -WindowStyle Hidden -RedirectStandardOutput $CodexAgentOutLog -RedirectStandardError $CodexAgentErrLog -PassThru
    }
    finally {
        foreach ($name in $savedEnv.Keys) {
            if ($null -eq $savedEnv[$name]) { Remove-Item -Path "Env:$name" -ErrorAction SilentlyContinue }
            else { Set-Item -Path "Env:$name" -Value $savedEnv[$name] -ErrorAction SilentlyContinue }
        }
    }
    Save-Pid -PidFile $PidCodex -Proc $codexProc
    Write-Host "Codex Feishu Agent PID: $($codexProc.Id)"
    Start-Sleep -Seconds 3
}

Write-Section "Lark CLI check"
Start-Process -FilePath "cmd.exe" -ArgumentList "/d", "/c", "set OPENCLAW_HOME= && set CLAW_HOME= && `"$LarkCliBin`" auth status" -WorkingDirectory $StackRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $LogDir "lark-check-out.log") -RedirectStandardError (Join-Path $LogDir "lark-check-err.log") -PassThru -Wait | Out-Null

Write-Section "Final status"
$openclawReady = Test-Port -Port $OpenClawPort
$moonReady = Test-Port -Port $MoonPort
$codexReady = Test-PidFileAlive -PidFile $PidCodex
$moonStatus = if ($NeedMoonBridge) { if ($moonReady) { "RUNNING" } else { "NOT READY" } } elseif ($moonReady) { "RUNNING (not required)" } else { "SKIPPED" }
Write-Host "OpenClaw Gateway : $(if ($openclawReady) { 'RUNNING' } else { 'NOT READY' })"
Write-Host "MoonBridge        : $moonStatus"
Write-Host "Codex Agent       : $(if ($codexReady) { 'RUNNING' } else { 'NOT READY' })"
Write-Host "Logs              : $LogDir"

if ($openclawReady -and $codexReady -and ((-not $NeedMoonBridge) -or $moonReady)) { exit 0 }
exit 1
