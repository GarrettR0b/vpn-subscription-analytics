from __future__ import annotations

from datetime import date
from pathlib import Path

from ai_saas_analytics.generator import generate_rows, write_rows
from ai_saas_analytics.metrics import activation_records
from ai_saas_analytics.settings import GeneratorSettings


def test_activation_metric_has_expected_population(tmp_path: Path) -> None:
    settings = GeneratorSettings(
        seed=20260830,
        start_date=date(2026, 1, 1),
        observation_days=180,
        experiment_start_day=60,
        workspace_count=250,
    )
    write_rows(generate_rows(settings), tmp_path)
    records = activation_records(tmp_path)
    activated_count = sum(record["activated_7d"] for record in records)
    variants = {record["experiment_variant"] for record in records}

    assert 0 < activated_count < len(records)
    assert {"control", "treatment"}.issubset(variants)
    assert all(
        record["accepted_suggestions_7d"] >= 3 for record in records if record["activated_7d"]
    )


def test_internal_workspaces_are_excluded(tmp_path: Path) -> None:
    settings = GeneratorSettings(17, date(2026, 1, 1), 180, 60, 500)
    generated = generate_rows(settings)
    write_rows(generated, tmp_path)
    internal_count = sum(row["is_internal"] == "true" for row in generated["workspaces"])

    assert internal_count > 0
    assert len(activation_records(tmp_path)) == settings.workspace_count - internal_count
