$StackRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)

$CodexHome = "E:\codeX"
$CodexBin = "E:\codeX\bin\codex.exe"
$CodexConfig = Join-Path $CodexHome "config.toml"
$CodexSwitchScript = Join-Path $StackRoot "codex\Switch-CodexProvider.ps1"
$CodexRestoreScript = Join-Path $StackRoot "codex\Restore-CodexNative.ps1"

$MoonDir = "E:\codeX\moon-bridge"
$MoonExe = "E:\codeX\moon-bridge\.cache\moonbridge.exe"
$MoonConfig = "E:\codeX\moon-bridge\config.yml"
$MoonPort = 38440

$OpenClawHome = "E:\openclaw\clawclaw"
$OpenClawGatewayCmd = "E:\openclaw\clawclaw\.openclaw\gateway.cmd"
$OpenClawPort = 18789

$AgentsDir = Join-Path $StackRoot "agents"
$CodexAgentDir = Join-Path $AgentsDir "feishu-codex-agent"
$CodexAgentEntry = Join-Path $CodexAgentDir "dist\src\index.js"
$OpenClawPluginDir = Join-Path $AgentsDir "feishu-bot-chat-plugin"
$LarkCliBin = Join-Path $StackRoot ".npm-global\node_modules\@larksuite\cli\bin\lark-cli.exe"

$RuntimeDir = Join-Path $StackRoot "runtime"
$LogDir = Join-Path $RuntimeDir "logs"
$PidDir = Join-Path $RuntimeDir "pids"

$PidOpenClaw = Join-Path $PidDir "openclaw-gateway.pid"
$PidMoon = Join-Path $PidDir "moonbridge.pid"
$PidCodex = Join-Path $PidDir "codex-agent.pid"

$OpenClawOutLog = Join-Path $LogDir "openclaw-gateway-out.log"
$OpenClawErrLog = Join-Path $LogDir "openclaw-gateway-err.log"
$MoonOutLog = Join-Path $LogDir "moonbridge-out.log"
$MoonErrLog = Join-Path $LogDir "moonbridge-err.log"
$CodexAgentOutLog = Join-Path $LogDir "codex-agent-out.log"
$CodexAgentErrLog = Join-Path $LogDir "codex-agent-err.log"

New-Item -ItemType Directory -Force -Path $RuntimeDir, $LogDir, $PidDir | Out-Null
