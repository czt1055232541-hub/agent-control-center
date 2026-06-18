$ErrorActionPreference = "Stop"

$CodexHome = "E:\codeX"
$ConfigToml = Join-Path $CodexHome "config.toml"
$NativeModel = "gpt-5.5"

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

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
$backupPath = Join-Path $CodexHome "config.toml.bak-restore-native-$timestamp"
Copy-Item -LiteralPath $ConfigToml -Destination $backupPath -Force

$lines = Read-ConfigLines -Path $ConfigToml
$lines = Set-TopLevelKey -Lines $lines -Key "model" -TomlValue "`"$NativeModel`""
$lines = Remove-TopLevelKeys -Lines $lines -Keys @(
    "model_provider",
    "model_context_window",
    "model_max_output_tokens",
    "model_catalog_json"
)
$lines = Remove-Section -Lines $lines -SectionName "model_providers.moonbridge"
Write-ConfigLines -Path $ConfigToml -Lines $lines

$verify = Read-ConfigLines -Path $ConfigToml
$verifiedModel = Get-TopLevelValue -Lines $verify -Key "model"
$verifiedProvider = Get-TopLevelValue -Lines $verify -Key "model_provider"
if ($verifiedModel -ne $NativeModel -or $verifiedProvider) {
    throw "Native restore verification failed. model=$verifiedModel provider=$verifiedProvider"
}
Remove-OldBackups -Pattern "config.toml.bak-restore-native-*" -KeepPath $backupPath

Write-Host "Codex restored to Native OpenAI mode."
Write-Host "Model: $NativeModel"
Write-Host "Backup: $backupPath"
