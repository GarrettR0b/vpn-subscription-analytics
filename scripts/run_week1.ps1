param(
    [ValidateSet("smoke", "small", "portfolio")]
    [string]$Profile = "small"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Push-Location $ProjectRoot
try {
    python -m ai_saas_analytics.generator --profile $Profile --sample-dir data/samples
    python -m ai_saas_analytics.data_quality
    docker compose up -d
    python -m ai_saas_analytics.loader
    python -m pytest
} finally {
    Pop-Location
}
