import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def report_copy(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "powerbi").mkdir()
    for name in ("build_powerbi_report.mjs", "powerbi-generated-visuals.json"):
        shutil.copy2(ROOT / "scripts" / name, tmp_path / "scripts" / name)
    shutil.copy2(ROOT / "powerbi/vpn-analytics.pbip", tmp_path / "powerbi/vpn-analytics.pbip")
    shutil.copytree(ROOT / "powerbi/vpn-analytics.Report", tmp_path / "powerbi/vpn-analytics.Report",
                    ignore=shutil.ignore_patterns(".pbi"))
    return tmp_path


@pytest.mark.skipif(not shutil.which("node"), reason="Node.js is not installed")
def test_generator_removes_its_old_visuals_but_preserves_manual_ones(report_copy):
    script = report_copy / "scripts/build_powerbi_report.mjs"
    source = script.read_text(encoding="utf-8")
    removed_line = next(line for line in source.splitlines() if "textbox('bo-note'" in line)
    script.write_text(source.replace(removed_line + "\n", ""), encoding="utf-8")
    removed_id = hashlib.sha1(b"bo-note").hexdigest()[:20]
    pages = report_copy / "powerbi/vpn-analytics.Report/definition/pages"
    removed = next(pages.glob(f"*/visuals/{removed_id}/visual.json"))
    manual = removed.parent.parent / ("f" * 20) / "visual.json"
    manual.parent.mkdir()
    content = json.loads(removed.read_text(encoding="utf-8"))
    content["name"] = "f" * 20
    manual.write_text(json.dumps(content), encoding="utf-8")
    result = subprocess.run(["node", str(script)], capture_output=True, text=True,
                            encoding="utf-8", check=True)
    status = json.loads(result.stdout)
    assert not removed.exists()
    assert json.loads(manual.read_text(encoding="utf-8")) == content
    assert status["generatedVisuals"] == 79
    assert status["visuals"] == len(list(pages.glob("*/visuals/*/visual.json"))) == 80


@pytest.mark.skipif(not shutil.which("node"), reason="Node.js is not installed")
def test_invalid_ownership_manifest_is_refused_before_writing(report_copy):
    (report_copy / "scripts/powerbi-generated-visuals.json").write_text(
        json.dumps({"../outside": ["f" * 20]}), encoding="utf-8",
    )
    report = report_copy / "powerbi/vpn-analytics.Report/definition/report.json"
    before = report.read_bytes()
    result = subprocess.run(["node", str(report_copy / "scripts/build_powerbi_report.mjs")],
                            capture_output=True, text=True, encoding="utf-8", check=False)
    assert result.returncode != 0
    assert "Invalid generated-visual manifest" in result.stderr
    assert report.read_bytes() == before
