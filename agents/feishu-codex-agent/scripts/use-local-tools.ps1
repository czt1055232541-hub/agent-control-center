$Root = Split-Path -Parent $PSScriptRoot
$WorkspaceRoot = Split-Path -Parent $Root
$NodeDir = Get-ChildItem -LiteralPath (Join-Path $WorkspaceRoot ".tools") -Directory -Filter "node-v*-win-x64" | Sort-Object Name -Descending | Select-Object -First 1
if (-not $NodeDir) {
  throw "Portable Node.js was not found under $WorkspaceRoot\.tools"
}
$NpmGlobal = Join-Path $WorkspaceRoot ".npm-global"
$env:PATH = "$NpmGlobal;$($NodeDir.FullName);$env:PATH"
$env:TEMP = Join-Path $WorkspaceRoot ".tmp"
$env:TMP = Join-Path $WorkspaceRoot ".tmp"
$env:HOME = Join-Path $WorkspaceRoot ".home"
$env:USERPROFILE = Join-Path $WorkspaceRoot ".home"
$env:APPDATA = Join-Path $WorkspaceRoot ".appdata"
$env:LOCALAPPDATA = Join-Path $WorkspaceRoot ".localappdata"
$env:npm_config_cache = Join-Path $WorkspaceRoot ".npm-cache"
$env:npm_config_prefix = Join-Path $WorkspaceRoot ".npm-global"
$env:npm_config_userconfig = Join-Path $WorkspaceRoot ".npmrc"
Write-Host "Local tools loaded from $WorkspaceRoot"
Write-Host "Run: npm install"
