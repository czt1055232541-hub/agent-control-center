param([switch]$NoPause)

$ErrorActionPreference = "Stop"
. (Join-Path (Split-Path -Parent $PSScriptRoot) "config\paths.ps1")

$shortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "Feishu Codex Control Center.lnk"
$target = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$script = Join-Path $StackRoot "scripts\start-control-center.ps1"
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$script`""

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $target
$shortcut.Arguments = $arguments
$shortcut.WorkingDirectory = $StackRoot
$shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,220"
$shortcut.Description = "Start Feishu Codex Control Center"
$shortcut.Save()

Write-Host "Created shortcut: $shortcutPath"
if (-not $NoPause) { Read-Host "Press Enter to close" | Out-Null }
