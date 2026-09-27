from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

from vpn_analytics.data_quality import validate_dataset
from vpn_analytics.generator import generate_rows, write_rows
from vpn_analytics.settings import GeneratorSettings


def _settings() -> GeneratorSettings:
    return GeneratorSettings(
        seed=20260830,
        start_date=date(2026, 1, 1),
        observation_days=181,
        regular_user_count=30,
        prospect_user_count=120,
    )


def _hashes(directory: Path) -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.glob("*.csv"))
    }


def test_generation_is_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    write_rows(generate_rows(_settings()), first)
    write_rows(generate_rows(_settings()), second)
    assert _hashes(first) == _hashes(second)


def test_generated_dataset_passes_quality_contract(tmp_path: Path) -> None:
    write_rows(generate_rows(_settings()), tmp_path)
    failures = [result for result in validate_dataset(tmp_path) if result.failure_count]
    assert failures == []
