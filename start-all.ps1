param(
    [ValidateSet("native", "moonbridge", "current")]
    [string]$CodexMode = "current",
    [switch]$NoPause
)

$script = Join-Path $PSScriptRoot "scripts\start-all.ps1"
& $script -CodexMode $CodexMode -NoPause:$NoPause
exit $LASTEXITCODE
