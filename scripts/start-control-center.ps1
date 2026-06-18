param(
    [switch]$NoOpen,
    [switch]$NoBuild,
    [switch]$NoPause
)

& "F:\1AI\Agent control center\scripts\start-control-center.ps1" @PSBoundParameters
exit $LASTEXITCODE
