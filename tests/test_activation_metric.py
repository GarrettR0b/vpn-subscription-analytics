from __future__ import annotations

from datetime import date
from pathlib import Path

from vpn_analytics.generator import generate_rows, write_rows
from vpn_analytics.metrics import user_activation_records
from vpn_analytics.settings import GeneratorSettings


def test_activation_metric_has_expected_population(tmp_path: Path) -> None:
    settings = GeneratorSettings(20260830, date(2026, 1, 1), 180, 60, 350)
    write_rows(generate_rows(settings), tmp_path)
    records = user_activation_records(tmp_path)
    activated_count = sum(record["activated_7d"] for record in records)
    variants = {record["experiment_variant"] for record in records}

    assert 0 < activated_count < len(records)
    assert {"control", "treatment"}.issubset(variants)
    assert all(
        record["successful_sessions_7d"] >= 3
        and record["active_days_7d"] >= 2
        and record["protected_minutes_7d"] >= 30
        for record in records
        if record["activated_7d"]
    )


def test_internal_users_are_excluded(tmp_path: Path) -> None:
    settings = GeneratorSettings(17, date(2026, 1, 1), 180, 60, 600)
    generated = generate_rows(settings)
    write_rows(generated, tmp_path)
    internal_count = sum(row["is_internal"] == "true" for row in generated["users"])

    assert internal_count > 0
    assert len(user_activation_records(tmp_path)) == settings.user_count - internal_count
