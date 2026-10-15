import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")


@pytest.mark.skipif(not POWERSHELL, reason="PowerShell is not installed")
@pytest.mark.parametrize("fail_at", [-1, 0, 1, 3, 6])
def test_pipeline_stops_after_first_native_failure(fail_at):
    executable = sys.executable.replace("'", "''")
    script = str(ROOT / "scripts/run_week1.ps1").replace("'", "''")
    confirmation = "" if fail_at == -1 else "-ResetDatabase vpn_analytics"
    result = subprocess.run([
        POWERSHELL, "-NoProfile", "-NonInteractive", "-Command", f"""
$global:Calls = [System.Collections.Generic.List[string]]::new()
$before = (Get-Location).Path
function python {{
    $global:Calls.Add(($args -join ' '))
    $code = if ($global:Calls.Count -eq {fail_at}) {{ 7 }} else {{ 0 }}
    & '{executable}' -c "import sys; sys.exit($code)"
}}
$failed = $false
try {{ & '{script}' -Profile smoke {confirmation} }}
catch {{ $failed = $true }}
@{{ calls = @($global:Calls); failed = $failed; restored = ((Get-Location).Path -eq $before) }} | ConvertTo-Json -Compress
""",
    ], capture_output=True, text=True, encoding="utf-8", check=True)
    status = json.loads(result.stdout)
    assert len(status["calls"]) == (0 if fail_at == -1 else fail_at or 6)
    assert status["failed"] == bool(fail_at)
    assert status["restored"]
    if len(status["calls"]) >= 3:
        assert "--reset-database vpn_analytics" in status["calls"][2]
