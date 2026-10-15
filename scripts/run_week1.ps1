param(
    [ValidateSet("smoke", "small", "portfolio")]
    [string]$Profile = "small",
    [string]$ResetDatabase
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($ResetDatabase)) {
    throw "Pass -ResetDatabase DATABASE_NAME to confirm replacement of core and analytics."
}

Push-Location $ProjectRoot
try {
    python -m vpn_analytics.generator --profile $Profile --sample-dir data/samples
    if ($LASTEXITCODE -ne 0) { throw "Data generation failed (exit $LASTEXITCODE)." }
    python -m vpn_analytics.data_quality
    if ($LASTEXITCODE -ne 0) { throw "CSV validation failed (exit $LASTEXITCODE)." }
    python -m vpn_analytics.loader --reset-database $ResetDatabase
    if ($LASTEXITCODE -ne 0) { throw "Database load failed (exit $LASTEXITCODE)." }
    python scripts/reconcile_postgres.py
    if ($LASTEXITCODE -ne 0) { throw "Reconciliation failed (exit $LASTEXITCODE)." }
    python scripts/create_starter_notebook.py
    if ($LASTEXITCODE -ne 0) { throw "Notebook build failed (exit $LASTEXITCODE)." }
    python -m pytest
    if ($LASTEXITCODE -ne 0) { throw "Tests failed (exit $LASTEXITCODE)." }
} finally {
    Pop-Location
}
