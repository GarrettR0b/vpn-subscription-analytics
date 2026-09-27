from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .settings import GeneratorSettings, load_generator_settings, project_root

TABLE_FIELDS: dict[str, list[str]] = {
    "users": [
        "user_id",
        "registered_at",
        "acquisition_channel",
        "country",
        "signup_platform",
        "is_internal",
        "source_seed",
    ],
    "devices": [
        "device_id",
        "user_id",
        "platform",
        "app_version",
        "installed_at",
        "first_open_at",
        "is_primary",
    ],
    "subscriptions": [
        "subscription_id",
        "user_id",
        "plan",
        "trial_started_at",
        "trial_ends_at",
        "converted_at",
        "ended_at",
        "status",
        "price_usd",
    ],
    "product_events": [
        "event_id",
        "user_id",
        "device_id",
        "session_id",
        "occurred_at",
        "event_name",
        "properties",
    ],
    "vpn_servers": [
        "server_id",
        "country",
        "city",
        "region",
        "provider",
        "capacity_mbps",
        "hourly_cost_usd",
        "launched_at",
        "is_active",
    ],
    "vpn_sessions": [
        "vpn_session_id",
        "user_id",
        "device_id",
        "server_id",
        "started_at",
        "ended_at",
        "connection_status",
        "protocol",
        "connection_time_ms",
        "bytes_down",
        "bytes_up",
        "disconnect_reason",
    ],
    "experiment_assignments": [
        "experiment_id",
        "user_id",
        "variant",
        "assigned_at",
        "stratum",
    ],
}


SERVER_LOCATIONS = [
    ("DE", "Frankfurt", "Europe"),
    ("NL", "Amsterdam", "Europe"),
    ("FI", "Helsinki", "Europe"),
    ("PL", "Warsaw", "Europe"),
    ("GB", "London", "Europe"),
    ("US", "New York", "North America"),
    ("US", "Chicago", "North America"),
    ("CA", "Toronto", "North America"),
    ("SG", "Singapore", "Asia"),
    ("JP", "Tokyo", "Asia"),
    ("KZ", "Almaty", "Central Asia"),
    ("GE", "Tbilisi", "Central Asia"),
]


def _iso(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _weighted(rng: random.Random, choices: list[tuple[Any, float]]) -> Any:
    return rng.choices(
        [choice for choice, _ in choices],
        weights=[weight for _, weight in choices],
        k=1,
    )[0]


def _bounded_lognormal(
    rng: random.Random,
    median: float,
    sigma: float,
    low: int,
    high: int,
) -> int:
    return min(high, max(low, int(rng.lognormvariate(math.log(median), sigma))))


def _event(
    rows: dict[str, list[dict[str, Any]]],
    user_id: str,
    device_id: str,
    occurred_at: datetime,
    event_name: str,
    sequence: int,
    properties: dict[str, Any] | None = None,
) -> None:
    user_suffix = user_id.removeprefix("usr_")
    rows["product_events"].append(
        {
            "event_id": f"evt_{user_suffix}_{sequence:04d}",
            "user_id": user_id,
            "device_id": device_id,
            "session_id": f"ses_{user_suffix}_{sequence // 5:03d}",
            "occurred_at": _iso(occurred_at),
            "event_name": event_name,
            "properties": json.dumps(properties or {}, sort_keys=True, separators=(",", ":")),
        }
    )


def _generate_servers(
    rng: random.Random,
    rows: dict[str, list[dict[str, Any]]],
    period_start: datetime,
) -> list[dict[str, Any]]:
    providers = [("cloud_a", 0.45), ("cloud_b", 0.35), ("colo_c", 0.20)]
    for index in range(1, 25):
        country, city, region = SERVER_LOCATIONS[(index - 1) % len(SERVER_LOCATIONS)]
        rows["vpn_servers"].append(
            {
                "server_id": f"srv_{index:03d}",
                "country": country,
                "city": city,
                "region": region,
                "provider": _weighted(rng, providers),
                "capacity_mbps": rng.choice([1000, 1500, 2000, 2500]),
                "hourly_cost_usd": f"{rng.uniform(0.16, 0.58):.4f}",
                "launched_at": _iso(period_start - timedelta(days=rng.randint(30, 180))),
                "is_active": "true",
            }
        )
    return rows["vpn_servers"]


def generate_rows(settings: GeneratorSettings) -> dict[str, list[dict[str, Any]]]:
    rng = random.Random(settings.seed)
    rows: dict[str, list[dict[str, Any]]] = {name: [] for name in TABLE_FIELDS}
    period_start = datetime.combine(settings.start_date, datetime.min.time(), tzinfo=UTC)
    observation_end = period_start + timedelta(days=settings.observation_days)
    servers = _generate_servers(rng, rows, period_start)

    channels = [
        ("organic", 0.29),
        ("content", 0.20),
        ("referral", 0.17),
        ("paid_search", 0.21),
        ("affiliate", 0.13),
    ]
    countries = [
        ("RU", 0.35),
        ("KZ", 0.14),
        ("BY", 0.08),
        ("AM", 0.07),
        ("GE", 0.07),
        ("DE", 0.08),
        ("US", 0.08),
        ("Other", 0.13),
    ]
    platforms = [("android", 0.46), ("ios", 0.31), ("windows", 0.18), ("macos", 0.05)]
    protocols = [("wireguard", 0.66), ("openvpn", 0.22), ("ikev2", 0.12)]

    for index in range(1, settings.user_count + 1):
        user_id = f"usr_{index:06d}"
        device_id = f"dev_{index:06d}_01"
        registered_at = period_start + timedelta(
            days=rng.randint(0, settings.observation_days - 14),
            seconds=rng.randint(6 * 3600, 23 * 3600),
        )
        acquisition_channel = _weighted(rng, channels)
        country = _weighted(rng, countries)
        platform = _weighted(rng, platforms)
        is_internal = rng.random() < 0.012
        user_seed = settings.seed + index * 7919

        rows["users"].append(
            {
                "user_id": user_id,
                "registered_at": _iso(registered_at),
                "acquisition_channel": acquisition_channel,
                "country": country,
                "signup_platform": platform,
                "is_internal": str(is_internal).lower(),
                "source_seed": user_seed,
            }
        )

        event_sequence = 1
        _event(
            rows,
            user_id,
            "",
            registered_at,
            "signup_completed",
            event_sequence,
            {"channel": acquisition_channel, "country": country},
        )
        event_sequence += 1

        age_day = (registered_at - period_start).days
        variant: str | None = None
        if age_day >= settings.experiment_start_day and not is_internal:
            variant = "treatment" if rng.random() < 0.5 else "control"
            rows["experiment_assignments"].append(
                {
                    "experiment_id": "smart_location_onboarding_v1",
                    "user_id": user_id,
                    "variant": variant,
                    "assigned_at": _iso(registered_at + timedelta(minutes=1)),
                    "stratum": f"{platform}:{acquisition_channel}",
                }
            )

        treatment_lift = 0.10 if variant == "treatment" else 0.0
        platform_modifier = 0.03 if platform in {"android", "ios"} else -0.02
        install_probability = min(0.98, 0.86 + treatment_lift * 0.35 + platform_modifier)
        installed_at: datetime | None = None
        first_open_at: datetime | None = None
        if rng.random() < install_probability:
            install_delay_hours = rng.uniform(0.05, 20 if variant == "treatment" else 32)
            installed_at = registered_at + timedelta(hours=install_delay_hours)
            first_open_at = installed_at + timedelta(minutes=rng.uniform(1, 35))
            app_version = f"3.{rng.randint(6, 9)}.{rng.randint(0, 5)}"
            rows["devices"].append(
                {
                    "device_id": device_id,
                    "user_id": user_id,
                    "platform": platform,
                    "app_version": app_version,
                    "installed_at": _iso(installed_at),
                    "first_open_at": _iso(first_open_at),
                    "is_primary": "true",
                }
            )
            _event(
                rows,
                user_id,
                device_id,
                installed_at,
                "app_installed",
                event_sequence,
                {"platform": platform, "app_version": app_version},
            )
            event_sequence += 1
            _event(
                rows,
                user_id,
                device_id,
                first_open_at,
                "app_opened",
                event_sequence,
                {"platform": platform},
            )
            event_sequence += 1

        plan = _weighted(rng, [("monthly", 0.67), ("annual", 0.33)])
        price_usd = 9.99 if plan == "monthly" else 79.99
        trial_started_at = registered_at + timedelta(minutes=5)
        trial_ends_at = trial_started_at + timedelta(days=7)
        _event(
            rows,
            user_id,
            device_id if installed_at else "",
            trial_started_at,
            "trial_started",
            event_sequence,
            {"plan": plan},
        )
        event_sequence += 1

        successful_early_sessions: list[tuple[datetime, datetime]] = []
        if first_open_at:
            engagement_score = rng.random() + treatment_lift
            if acquisition_channel in {"organic", "referral"}:
                engagement_score += 0.06
            if engagement_score < 0.16:
                early_attempts = 0
            elif engagement_score < 0.38:
                early_attempts = rng.randint(1, 2)
            elif engagement_score < 0.70:
                early_attempts = rng.randint(3, 5)
            else:
                early_attempts = rng.randint(6, 10)

            early_days: list[int] = []
            if early_attempts >= 3 and engagement_score >= 0.38:
                early_days.extend([0, rng.randint(1, 3)])
            while len(early_days) < early_attempts:
                early_days.append(rng.randint(0, 6))
            early_days.sort()
            later_attempts = rng.randint(0, min(8, early_attempts + 2))
            session_days = early_days + sorted(rng.randint(8, 30) for _ in range(later_attempts))

            recommended_server = rng.choice(servers)
            protocol = _weighted(rng, protocols)
            _event(
                rows,
                user_id,
                device_id,
                first_open_at + timedelta(minutes=1),
                "server_list_viewed",
                event_sequence,
                {"recommended_server_id": recommended_server["server_id"]},
            )
            event_sequence += 1
            _event(
                rows,
                user_id,
                device_id,
                first_open_at + timedelta(minutes=2),
                "protocol_selected",
                event_sequence,
                {"protocol": protocol, "automatic": variant == "treatment"},
            )
            event_sequence += 1

            for session_index, session_day in enumerate(session_days, start=1):
                session_at = first_open_at + timedelta(
                    days=session_day,
                    hours=rng.uniform(0.1, 12),
                )
                if session_at >= observation_end:
                    continue
                server = recommended_server if rng.random() < 0.56 else rng.choice(servers)
                chosen_protocol = protocol if rng.random() < 0.78 else _weighted(rng, protocols)
                failure_probability = 0.15 - (0.055 if variant == "treatment" else 0.0)
                failure_probability += 0.025 if chosen_protocol == "openvpn" else 0.0
                succeeded = rng.random() >= failure_probability
                base_connection_median = 1050 if variant == "treatment" else 1450
                connection_time_ms = _bounded_lognormal(
                    rng,
                    median=base_connection_median,
                    sigma=0.72,
                    low=140,
                    high=12000,
                )

                if succeeded:
                    duration_minutes = min(
                        150,
                        max(3, rng.lognormvariate(math.log(22), 0.72)),
                    )
                    ended_at = session_at + timedelta(minutes=duration_minutes)
                    throughput_mbps = rng.uniform(5, 24)
                    bytes_down = int(duration_minutes * 60 * throughput_mbps * 125_000)
                    bytes_up = int(bytes_down * rng.uniform(0.08, 0.28))
                    disconnect_reason = _weighted(
                        rng,
                        [("user_disconnected", 0.67), ("app_closed", 0.26), ("network_lost", 0.07)],
                    )
                    if session_at < registered_at + timedelta(days=7):
                        successful_early_sessions.append((session_at, ended_at))
                    event_name = "vpn_connection_succeeded"
                    event_properties = {
                        "server_id": server["server_id"],
                        "protocol": chosen_protocol,
                    }
                else:
                    ended_at = None
                    bytes_down = 0
                    bytes_up = 0
                    disconnect_reason = _weighted(
                        rng,
                        [
                            ("timeout", 0.36),
                            ("server_unreachable", 0.28),
                            ("dns_error", 0.21),
                            ("auth_error", 0.15),
                        ],
                    )
                    event_name = "vpn_connection_failed"
                    event_properties = {
                        "error_code": disconnect_reason,
                        "protocol": chosen_protocol,
                    }

                rows["vpn_sessions"].append(
                    {
                        "vpn_session_id": f"vpn_{index:06d}_{session_index:03d}",
                        "user_id": user_id,
                        "device_id": device_id,
                        "server_id": server["server_id"],
                        "started_at": _iso(session_at),
                        "ended_at": _iso(ended_at),
                        "connection_status": "success" if succeeded else "failed",
                        "protocol": chosen_protocol,
                        "connection_time_ms": connection_time_ms,
                        "bytes_down": bytes_down,
                        "bytes_up": bytes_up,
                        "disconnect_reason": disconnect_reason,
                    }
                )
                _event(
                    rows,
                    user_id,
                    device_id,
                    session_at + timedelta(milliseconds=connection_time_ms),
                    event_name,
                    event_sequence,
                    event_properties,
                )
                event_sequence += 1

        protected_minutes = sum(
            (ended_at - started_at).total_seconds() / 60
            for started_at, ended_at in successful_early_sessions
        )
        active_days = len({started_at.date() for started_at, _ in successful_early_sessions})
        activated_proxy = (
            installed_at is not None
            and installed_at < registered_at + timedelta(days=7)
            and len(successful_early_sessions) >= 3
            and active_days >= 2
            and protected_minutes >= 30
        )
        conversion_probability = 0.16 + (0.51 if activated_proxy else 0.0)
        if acquisition_channel in {"organic", "referral"}:
            conversion_probability += 0.05
        converted = rng.random() < min(0.90, conversion_probability)
        converted_at = trial_ends_at - timedelta(hours=rng.uniform(1, 30)) if converted else None
        ended_at: datetime | None = None
        if converted_at:
            cancelled = rng.random() < 0.07
            if cancelled:
                ended_at = converted_at + timedelta(days=rng.uniform(8, 55))
                if ended_at <= observation_end:
                    status = "cancelled"
                else:
                    ended_at = None
                    status = "active"
            else:
                status = "active"
        else:
            status = "expired"

        rows["subscriptions"].append(
            {
                "subscription_id": f"sub_{index:06d}",
                "user_id": user_id,
                "plan": plan,
                "trial_started_at": _iso(trial_started_at),
                "trial_ends_at": _iso(trial_ends_at),
                "converted_at": _iso(converted_at),
                "ended_at": _iso(ended_at),
                "status": status,
                "price_usd": f"{price_usd:.2f}",
            }
        )
        if converted_at:
            _event(
                rows,
                user_id,
                device_id if installed_at else "",
                converted_at,
                "subscription_converted",
                event_sequence,
                {"plan": plan, "price_usd": price_usd},
            )

    return rows


def write_rows(
    rows: dict[str, list[dict[str, Any]]],
    output_dir: Path,
    sample_dir: Path | None = None,
) -> dict[str, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if sample_dir:
        sample_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for table_name, fields in TABLE_FIELDS.items():
        table_rows = rows[table_name]
        counts[table_name] = len(table_rows)
        with (output_dir / f"{table_name}.csv").open(
            "w", newline="", encoding="utf-8"
        ) as output_file:
            writer = csv.DictWriter(output_file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(table_rows)
        if sample_dir:
            with (sample_dir / f"{table_name}.sample.csv").open(
                "w", newline="", encoding="utf-8"
            ) as sample_file:
                writer = csv.DictWriter(sample_file, fieldnames=fields)
                writer.writeheader()
                writer.writerows(table_rows[:10])
    return counts


def _arguments(argv: Iterable[str] | None = None) -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser(description="Generate deterministic synthetic VPN data.")
    parser.add_argument("--profile", default="small", choices=("smoke", "small", "portfolio"))
    parser.add_argument("--config", type=Path, default=root / "config" / "generator.toml")
    parser.add_argument("--output-dir", type=Path, default=root / "data" / "generated")
    parser.add_argument("--sample-dir", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=None)
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = _arguments(argv)
    settings = load_generator_settings(args.config, args.profile, args.seed)
    rows = generate_rows(settings)
    counts = write_rows(rows, args.output_dir, args.sample_dir)
    manifest = {
        "profile": args.profile,
        "seed": settings.seed,
        "start_date": settings.start_date.isoformat(),
        "observation_days": settings.observation_days,
        "experiment_start_day": settings.experiment_start_day,
        "counts": counts,
    }
    with (args.output_dir / "manifest.json").open("w", encoding="utf-8") as manifest_file:
        json.dump(manifest, manifest_file, ensure_ascii=False, indent=2, sort_keys=True)
        manifest_file.write("\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
