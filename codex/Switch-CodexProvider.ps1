<#
.SYNOPSIS
    Switch Codex between Native OpenAI and MoonBridge/DeepSeek mode.
.DESCRIPTION
    Field-level switcher for E:\codeX\config.toml.
    It preserves desktop, plugins, MCP, projects, auth, and session state.
#>

[CmdletBinding()]
param(
    [ValidateSet("toggle", "native", "moonbridge")]
    [string]$Mode = "toggle",

    [switch]$AllowUnavailableMoonBridge
)

$ErrorActionPreference = "Stop"

$CodexHome = "E:\codeX"
$ConfigToml = Join-Path $CodexHome "config.toml"
$NativeModel = "gpt-5.5"
$MoonModel = "moonbridge"
$MoonPort = 38440
$MoonBaseUrl = "http://127.0.0.1:$MoonPort/v1"
$MoonCatalog = Join-Path $CodexHome "models_catalog.json"
$MoonCatalogSource = Join-Path $CodexHome "models_catalog.json.bak-switch"

function Read-ConfigLines {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "config.toml not found: $Path"
    }
    return [string[]][System.IO.File]::ReadAllLines($Path)
}

function Write-ConfigLines {
    param([string]$Path, [string[]]$Lines)
    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllLines($Path, $Lines, $utf8NoBom)
}

function Get-FirstSectionIndex {
    param([string[]]$Lines)
    for ($i = 0; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i] -match '^\s*\[') {
            return $i
        }
    }
    return $Lines.Count
}

function Get-TopLevelValue {
    param([string[]]$Lines, [string]$Key)
    $sectionStart = Get-FirstSectionIndex -Lines $Lines
    for ($i = 0; $i -lt $sectionStart; $i++) {
        if ($Lines[$i] -match "^\s*$([regex]::Escape($Key))\s*=\s*(.+?)\s*$") {
            return $Matches[1].Trim().Trim('"')
        }
    }
    return $null
}

function Set-TopLevelKey {
    param([string[]]$Lines, [string]$Key, [string]$TomlValue)
    $list = [System.Collections.Generic.List[string]]::new([string[]]$Lines)
    $sectionStart = Get-FirstSectionIndex -Lines ([string[]]$list)
    for ($i = 0; $i -lt $sectionStart; $i++) {
        if ($list[$i] -match "^\s*$([regex]::Escape($Key))\s*=") {
            $list[$i] = "$Key = $TomlValue"
            return [string[]]$list
        }
    }
    $insertAt = $sectionStart
    while ($insertAt -gt 0 -and [string]::IsNullOrWhiteSpace($list[$insertAt - 1])) {
        $insertAt--
    }
    $list.Insert($insertAt, "$Key = $TomlValue")
    return [string[]]$list
}

function Remove-TopLevelKeys {
    param([string[]]$Lines, [string[]]$Keys)
    $sectionStart = Get-FirstSectionIndex -Lines $Lines
    $out = [System.Collections.Generic.List[string]]::new()
    for ($i = 0; $i -lt $Lines.Count; $i++) {
        $remove = $false
        if ($i -lt $sectionStart) {
            foreach ($key in $Keys) {
                if ($Lines[$i] -match "^\s*$([regex]::Escape($key))\s*=") {
                    $remove = $true
                    break
                }
            }
        }
        if (-not $remove) {
            $out.Add($Lines[$i])
        }
    }
    return [string[]]$out
}

function Remove-Section {
    param([string[]]$Lines, [string]$SectionName)
    $out = [System.Collections.Generic.List[string]]::new()
    $skip = $false
    for ($i = 0; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i] -match "^\s*\[$([regex]::Escape($SectionName))\]\s*$") {
            $skip = $true
            continue
        }
        if ($skip -and $Lines[$i] -match '^\s*\[') {
            $skip = $false
        }
        if (-not $skip) {
            $out.Add($Lines[$i])
        }
    }
    return [string[]]$out
}

function Add-Section {
    param([string[]]$Lines, [string[]]$SectionLines)
    $list = [System.Collections.Generic.List[string]]::new([string[]]$Lines)
    while ($list.Count -gt 0 -and [string]::IsNullOrWhiteSpace($list[$list.Count - 1])) {
        $list.RemoveAt($list.Count - 1)
    }
    $list.Add("")
    foreach ($line in $SectionLines) {
        $list.Add($line)
    }
    return [string[]]$list
}

function Test-MoonBridgeReady {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "$MoonBaseUrl/models" -TimeoutSec 3
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500)
    }
    catch {
        return $false
    }
}

function Get-CurrentMode {
    param([string[]]$Lines)
    if ((Get-TopLevelValue -Lines $Lines -Key "model_provider") -eq "moonbridge") {
        return "moonbridge"
    }
    return "native"
}

function Apply-NativeMode {
    param([string[]]$Lines)
    $result = Set-TopLevelKey -Lines $Lines -Key "model" -TomlValue "`"$NativeModel`""
    $result = Remove-TopLevelKeys -Lines $result -Keys @(
        "model_provider",
        "model_context_window",
        "model_max_output_tokens",
        "model_catalog_json"
    )
    $result = Remove-Section -Lines $result -SectionName "model_providers.moonbridge"
    return [string[]]$result
}

function Apply-MoonBridgeMode {
    param([string[]]$Lines)
    if (-not (Test-MoonBridgeReady) -and -not $AllowUnavailableMoonBridge) {
        throw "MoonBridge is not reachable at $MoonBaseUrl. Start it first or pass -AllowUnavailableMoonBridge."
    }
    if (-not (Test-Path -LiteralPath $MoonCatalog) -and (Test-Path -LiteralPath $MoonCatalogSource)) {
        Copy-Item -LiteralPath $MoonCatalogSource -Destination $MoonCatalog -Force
    }
    if (-not (Test-Path -LiteralPath $MoonCatalog)) {
        throw "MoonBridge model catalog not found: $MoonCatalog"
    }
    $catalogToml = $MoonCatalog.Replace('\', '\\')
    $result = Set-TopLevelKey -Lines $Lines -Key "model" -TomlValue "`"$MoonModel`""
    $result = Set-TopLevelKey -Lines $result -Key "model_provider" -TomlValue "`"moonbridge`""
    $result = Set-TopLevelKey -Lines $result -Key "model_context_window" -TomlValue "1000000"
    $result = Set-TopLevelKey -Lines $result -Key "model_catalog_json" -TomlValue "`"$catalogToml`""
    $result = Remove-Section -Lines $result -SectionName "model_providers.moonbridge"
    $result = Add-Section -Lines $result -SectionLines @(
        "[model_providers.moonbridge]",
        'name = "Moon Bridge"',
        "base_url = `"$MoonBaseUrl`"",
        'wire_api = "responses"'
    )
    return [string[]]$result
}

function Assert-Mode {
    param([string]$ExpectedMode)
    $actual = Read-ConfigLines -Path $ConfigToml
    $actualMode = Get-CurrentMode -Lines $actual
    $actualModel = Get-TopLevelValue -Lines $actual -Key "model"
    if ($ExpectedMode -eq "moonbridge") {
        if ($actualMode -ne "moonbridge" -or $actualModel -ne $MoonModel) {
            throw "Switch verification failed. Expected moonbridge/$MoonModel, got $actualMode/$actualModel."
        }
    }
    elseif ($ExpectedMode -eq "native") {
        if ($actualMode -ne "native" -or $actualModel -ne $NativeModel) {
            throw "Switch verification failed. Expected native/$NativeModel, got $actualMode/$actualModel."
        }
    }
}

function Remove-OldBackups {
    param(
        [string]$Pattern,
        [string]$KeepPath
    )
    Get-ChildItem -LiteralPath $CodexHome -File -Filter $Pattern -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -ne $KeepPath } |
        Sort-Object LastWriteTime -Descending |
        ForEach-Object {
            Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
        }
}

$lines = Read-ConfigLines -Path $ConfigToml
$currentMode = Get-CurrentMode -Lines $lines
$currentModel = Get-TopLevelValue -Lines $lines -Key "model"
$targetMode = if ($Mode -eq "toggle") {
    if ($currentMode -eq "moonbridge") { "native" } else { "moonbridge" }
}
else {
    $Mode
}

Write-Host ""
Write-Host "========================================"
Write-Host "  Codex Provider Switcher"
Write-Host "========================================"
Write-Host "Current mode : $currentMode"
Write-Host "Current model: $currentModel"
Write-Host "Target mode  : $targetMode"
Write-Host ""

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
$backupPath = Join-Path $CodexHome "config.toml.bak-switch-$timestamp"
Copy-Item -LiteralPath $ConfigToml -Destination $backupPath -Force

if ($targetMode -eq "native") {
    $newLines = Apply-NativeMode -Lines $lines
}
elseif ($targetMode -eq "moonbridge") {
    $newLines = Apply-MoonBridgeMode -Lines $lines
}
else {
    throw "Unsupported target mode: $targetMode"
}

Write-ConfigLines -Path $ConfigToml -Lines $newLines
Assert-Mode -ExpectedMode $targetMode
Remove-OldBackups -Pattern "config.toml.bak-switch-*" -KeepPath $backupPath

Write-Host "Switch complete."
Write-Host "Verified mode: $targetMode"
Write-Host "Backup: $backupPath"
Write-Host "Restart Codex Desktop or start a new Codex process for the change to fully apply."
