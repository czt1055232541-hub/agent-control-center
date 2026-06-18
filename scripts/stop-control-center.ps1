param([switch]$NoPause)

$ErrorActionPreference = "Continue"
. (Join-Path (Split-Path -Parent $PSScriptRoot) "config\paths.ps1")

$ApiPort = 8765
$PidControlCenter = Join-Path $PidDir "control-center-api.pid"

function Stop-ByPidFile {
    param([string]$PidFile)
    if (-not (Test-Path -LiteralPath $PidFile)) { return $false }
    try {
        $pidText = Get-Content -LiteralPath $PidFile -ErrorAction Stop | Select-Object -First 1
        if (-not [string]::IsNullOrWhiteSpace($pidText)) {
            $proc = Get-Process -Id ([int]$pidText) -ErrorAction SilentlyContinue
            if ($proc -ne $null) {
                Stop-Process -Id ([int]$pidText) -Force -ErrorAction SilentlyContinue
            }
        }
        Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
        return $true
    }
    catch {
        Write-Host "Failed to stop by PID file: $($_.Exception.Message)"
        return $false
    }
}

function Stop-ByPort {
    param([int]$Port)
    $lines = netstat -ano | Select-String ":$Port"
    foreach ($line in $lines) {
        $text = $line.ToString().Trim()
        if ($text -match "LISTENING\s+(\d+)$") {
            $pidValue = [int]$matches[1]
            $proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
            if ($proc -and ($proc.ProcessName -match "python")) {
                Stop-Process -Id $pidValue -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

Stop-ByPidFile -PidFile $PidControlCenter | Out-Null
Stop-ByPort -Port $ApiPort

Write-Host "Control Center API stop requested. Other agents and Codex Desktop were not stopped."
if (-not $NoPause) { Read-Host "Press Enter to close" | Out-Null }
