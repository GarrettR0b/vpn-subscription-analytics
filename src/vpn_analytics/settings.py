from __future__ import annotations

import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class GeneratorSettings:
    seed: int
    start_date: date
    observation_days: int
    regular_user_count: int
    prospect_user_count: int

    @property
    def user_count(self) -> int:
        return self.regular_user_count + self.prospect_user_count


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_generator_settings(
    config_path: Path,
    profile: str,
    seed_override: int | None = None,
) -> GeneratorSettings:
    with config_path.open("rb") as config_file:
        raw = tomllib.load(config_file)

    profiles = raw.get("profiles", {})
    if profile not in profiles:
        available = ", ".join(sorted(profiles))
        raise ValueError(f"Unknown profile '{profile}'. Available profiles: {available}")

    project = raw["project"]
    return GeneratorSettings(
        seed=seed_override if seed_override is not None else int(project["seed"]),
        start_date=date.fromisoformat(project["start_date"]),
        observation_days=int(project["observation_days"]),
        regular_user_count=int(profiles[profile]["regular_users"]),
        prospect_user_count=int(profiles[profile]["prospects"]),
    )
