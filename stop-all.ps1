param([switch]$NoPause)

$script = Join-Path $PSScriptRoot "scripts\stop-all.ps1"
& $script -NoPause:$NoPause
exit $LASTEXITCODE
