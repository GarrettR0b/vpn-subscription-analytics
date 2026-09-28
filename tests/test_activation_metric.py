from __future__ import annotations

from datetime import date
from pathlib import Path

from vpn_analytics.generator import generate_rows, write_rows
from vpn_analytics.metrics import (
    activation_experiment_records,
    activation_experiment_statistics,
    monthly_business_records,
    subscriber_activation_records,
    subscriber_retention_records,
)
from vpn_analytics.settings import GeneratorSettings


def test_activation_metric_has_expected_population(tmp_path: Path) -> None:
    settings = GeneratorSettings(20260830, date(2026, 1, 1), 181, 50, 300)
    write_rows(generate_rows(settings), tmp_path)
    records = subscriber_activation_records(tmp_path)
    activated_count = sum(record["activated_7d"] for record in records)

    assert records
    assert 0 < activated_count < len(records)
    assert all(
        record["first_link_fetched_at"] is not None
        and record["successful_sessions_7d"] >= 3
        and record["active_days_7d"] >= 2
        and record["protected_minutes_7d"] >= 30
        for record in records
        if record["activated_7d"]
    )


def test_regular_monthly_base_matches_target(tmp_path: Path) -> None:
    settings = GeneratorSettings(20260830, date(2026, 1, 1), 181, 40, 365)
    write_rows(generate_rows(settings), tmp_path)
    monthly = monthly_business_records(tmp_path)

    assert {record["regular_paid_users"] for record in monthly} == {settings.regular_user_count}
    assert all(
        record["ending_paid_subscribers"]
        == record["basic_active_subscribers"] + record["pro_active_subscribers"]
        for record in monthly
    )
    new_users = [record["new_paid_users"] for record in monthly]
    assert 20 <= max(new_users) - min(new_users) < 100


def test_retention_has_baseline_and_real_dropoff(tmp_path: Path) -> None:
    settings = GeneratorSettings(20260830, date(2026, 1, 1), 181, 40, 365)
    write_rows(generate_rows(settings), tmp_path)
    records = subscriber_retention_records(tmp_path)
    baseline = [record for record in records if record["month_number"] == 0]
    month_one = [record for record in records if record["month_number"] == 1]

    assert baseline and month_one
    assert all(record["retained"] for record in baseline)
    assert 0 < sum(record["retained"] for record in month_one) < len(month_one)


def test_experiment_has_two_groups_and_valid_inference(tmp_path: Path) -> None:
    settings = GeneratorSettings(20260830, date(2026, 1, 1), 181, 40, 365)
    write_rows(generate_rows(settings), tmp_path)
    records = activation_experiment_records(tmp_path)
    result = activation_experiment_statistics(records)

    assert abs(result["controlSubscriptions"] - result["treatmentSubscriptions"]) <= 8
    assert result["treatmentActivationRate"] > result["controlActivationRate"]
    assert 0 <= result["pValue"] <= 1
    assert result["ciLow"] <= result["absoluteEffect"] <= result["ciHigh"]
