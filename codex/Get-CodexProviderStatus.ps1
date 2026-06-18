. (Join-Path (Split-Path -Parent (Split-Path -Parent $PSCommandPath)) "config\paths.ps1")

$config = if (Test-Path -LiteralPath $CodexConfig) { Get-Content -Raw -LiteralPath $CodexConfig } else { "" }
$model = if ($config -match '(?m)^model\s*=\s*"([^"]+)"') { $Matches[1] } else { "unknown" }
$provider = if ($config -match '(?m)^model_provider\s*=\s*"([^"]+)"') { $Matches[1] } else { "openai/default" }
$catalog = if ($config -match '(?m)^model_catalog_json\s*=\s*"([^"]+)"') { $Matches[1] } else { "" }

$moonReady = $false
try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$MoonPort/v1/models" -TimeoutSec 3
    $moonReady = ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500)
}
catch {
    $moonReady = $false
}

[pscustomobject]@{
    Model = $model
    Provider = $provider
    Catalog = $catalog
    CodexHome = $CodexHome
    Config = $CodexConfig
    MoonBridgeReady = $moonReady
    MoonBridgeUrl = "http://127.0.0.1:$MoonPort/v1"
} | Format-List
