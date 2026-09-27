param(
    [ValidateSet("smoke", "small", "portfolio")]
    [string]$Profile = "small"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Push-Location $ProjectRoot
try {
    python -m vpn_analytics.generator --profile $Profile --sample-dir data/samples
    python -m vpn_analytics.data_quality
    docker compose up -d
    python -m vpn_analytics.loader
    python scripts/reconcile_postgres.py
    python scripts/create_starter_notebook.py
    python -m pytest
} finally {
    Pop-Location
}
