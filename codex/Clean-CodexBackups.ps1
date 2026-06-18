param(
    [int]$Keep = 1
)

. (Join-Path (Split-Path -Parent (Split-Path -Parent $PSCommandPath)) "config\paths.ps1")

function Clean-Pattern {
    param([string]$Pattern)
    $files = Get-ChildItem -LiteralPath $CodexHome -File -Filter $Pattern -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending
    $remove = $files | Select-Object -Skip $Keep
    foreach ($file in $remove) {
        Remove-Item -LiteralPath $file.FullName -Force
        Write-Host "Removed $($file.FullName)"
    }
    Write-Host "$Pattern kept: $([Math]::Min($Keep, @($files).Count))"
}

Clean-Pattern -Pattern "config.toml.bak-switch-*"
Clean-Pattern -Pattern "config.toml.bak-restore-native-*"
Write-Host "config.toml.bak-goal-* files are preserved."
