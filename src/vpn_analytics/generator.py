from __future__ import annotations

import argparse
import csv
import json
import math
import random
from calendar import monthrange
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .settings import GeneratorSettings, load_generator_settings, project_root

TABLE_FIELDS: dict[str, list[str]] = {
    "dataset_periods": [
        "dataset_id",
        "period_start",
        "period_end",
        "timezone",
        "regular_user_target",
    ],
    "users": [
        "user_id",
        "registered_at",
        "acquisition_channel",
        "country",
        "signup_source",
        "is_internal",
        "source_seed",
    ],
    "subscriptions": [
        "subscription_id",
        "user_id",
        "sales_channel",
        "plan",
        "purchased_at",
        "starts_at",
        "ends_at",
        "status",
        "auto_renew",
        "price_rub",
        "currency",
    ],
    "subscription_links": [
        "subscription_link_id",
        "subscription_id",
        "user_id",
        "issued_at",
        "first_fetched_at",
        "last_fetched_at",
        "fetch_count",
        "client_name",
    ],
    "payments": [
        "payment_id",
        "subscription_id",
        "user_id",
        "paid_at",
        "amount_rub",
        "currency",
        "payment_type",
        "payment_status",
        "sales_channel",
    ],
    "proxy_servers": [
        "server_id",
        "country",
        "city",
        "region",
        "provider",
        "capacity_mbps",
        "monthly_cost_rub",
        "launched_at",
        "is_active",
    ],
    "proxy_sessions": [
        "proxy_session_id",
        "user_id",
        "subscription_id",
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
}

SERVER_LOCATIONS = [
    ("DE", "Frankfurt", "Europe"),
    ("NL", "Amsterdam", "Europe"),
    ("FI", "Helsinki", "Europe"),
    ("PL", "Warsaw", "Europe"),
    ("GB", "London", "Europe"),
    ("US", "New York", "North America"),
    ("CA", "Toronto", "North America"),
    ("SG", "Singapore", "Asia"),
    ("JP", "Tokyo", "Asia"),
    ("KZ", "Almaty", "Central Asia"),
    ("GE", "Tbilisi", "Central Asia"),
]

PLAN_MONTHS = {"one_month": 1, "three_months": 3, "twelve_months": 12}
PLAN_PRICES = {"one_month": 349, "three_months": 899, "twelve_months": 2990}


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


def _add_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _month_windows(start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    cursor = datetime(start.year, start.month, 1, tzinfo=UTC)
    windows: list[tuple[datetime, datetime]] = []
    while cursor < end:
        next_month = _add_months(cursor, 1)
        windows.append((max(cursor, start), min(next_month, end)))
        cursor = next_month
    return windows


def _random_time(
    rng: random.Random,
    start: datetime,
    end: datetime,
    margin_minutes: int = 180,
) -> datetime:
    seconds = max(1, int((end - start).total_seconds()) - margin_minutes * 60)
    return start + timedelta(seconds=rng.randint(0, seconds))


def _generate_servers(
    rng: random.Random,
    rows: dict[str, list[dict[str, Any]]],
    period_start: datetime,
) -> list[dict[str, Any]]:
    providers = [("cloud_a", 0.50), ("cloud_b", 0.32), ("colo_c", 0.18)]
    for index in range(1, 19):
        country, city, region = SERVER_LOCATIONS[(index - 1) % len(SERVER_LOCATIONS)]
        rows["proxy_servers"].append(
            {
                "server_id": f"srv_{index:03d}",
                "country": country,
                "city": city,
                "region": region,
                "provider": _weighted(rng, providers),
                "capacity_mbps": rng.choice([1000, 1500, 2000, 2500]),
                "monthly_cost_rub": rng.choice([3900, 4900, 6500, 7900]),
                "launched_at": _iso(period_start - timedelta(days=rng.randint(90, 720))),
                "is_active": "true",
            }
        )
    return rows["proxy_servers"]


def _add_payment(
    rows: dict[str, list[dict[str, Any]]],
    user_index: int,
    sequence: int,
    subscription_id: str,
    user_id: str,
    paid_at: datetime,
    amount_rub: int,
    payment_type: str,
    sales_channel: str,
) -> None:
    rows["payments"].append(
        {
            "payment_id": f"pay_{user_index:06d}_{sequence:02d}",
            "subscription_id": subscription_id,
            "user_id": user_id,
            "paid_at": _iso(paid_at),
            "amount_rub": amount_rub,
            "currency": "RUB",
            "payment_type": payment_type,
            "payment_status": "succeeded",
            "sales_channel": sales_channel,
        }
    )


def _add_session(
    rows: dict[str, list[dict[str, Any]]],
    rng: random.Random,
    user_index: int,
    sequence: int,
    user_id: str,
    subscription_id: str,
    servers: list[dict[str, Any]],
    started_at: datetime,
    force_success: bool = False,
    failure_rate: float = 0.07,
) -> None:
    server = rng.choice(servers)
    protocol = _weighted(rng, [("vless", 0.58), ("trojan", 0.24), ("shadowsocks", 0.18)])
    succeeded = force_success or rng.random() >= failure_rate
    connection_time_ms = _bounded_lognormal(rng, 820, 0.66, 110, 9000)
    if succeeded:
        duration_minutes = min(175, max(4, rng.lognormvariate(math.log(28), 0.72)))
        ended_at = started_at + timedelta(minutes=duration_minutes)
        throughput_mbps = rng.uniform(6, 32)
        bytes_down = int(duration_minutes * 60 * throughput_mbps * 125_000)
        bytes_up = int(bytes_down * rng.uniform(0.07, 0.24))
        disconnect_reason = _weighted(
            rng,
            [("client_closed", 0.78), ("idle_timeout", 0.16), ("network_lost", 0.06)],
        )
    else:
        ended_at = None
        bytes_down = 0
        bytes_up = 0
        disconnect_reason = _weighted(
            rng,
            [("timeout", 0.44), ("server_unreachable", 0.31), ("auth_error", 0.25)],
        )
    rows["proxy_sessions"].append(
        {
            "proxy_session_id": f"pxy_{user_index:06d}_{sequence:04d}",
            "user_id": user_id,
            "subscription_id": subscription_id,
            "server_id": server["server_id"],
            "started_at": _iso(started_at),
            "ended_at": _iso(ended_at),
            "connection_status": "success" if succeeded else "failed",
            "protocol": protocol,
            "connection_time_ms": connection_time_ms,
            "bytes_down": bytes_down,
            "bytes_up": bytes_up,
            "disconnect_reason": disconnect_reason,
        }
    )


def generate_rows(settings: GeneratorSettings) -> dict[str, list[dict[str, Any]]]:
    rng = random.Random(settings.seed)
    rows: dict[str, list[dict[str, Any]]] = {name: [] for name in TABLE_FIELDS}
    period_start = datetime.combine(settings.start_date, datetime.min.time(), tzinfo=UTC)
    period_end = period_start + timedelta(days=settings.observation_days)
    rows["dataset_periods"].append(
        {
            "dataset_id": "portfolio_v1",
            "period_start": _iso(period_start),
            "period_end": _iso(period_end),
            "timezone": "UTC",
            "regular_user_target": settings.regular_user_count,
        }
    )
    servers = _generate_servers(rng, rows, period_start)

    acquisition_channels = [
        ("organic", 0.32),
        ("referral", 0.24),
        ("telegram_ads", 0.19),
        ("paid_search", 0.15),
        ("affiliate", 0.10),
    ]
    countries = [
        ("RU", 0.48),
        ("KZ", 0.16),
        ("BY", 0.09),
        ("AM", 0.07),
        ("GE", 0.07),
        ("Other", 0.13),
    ]
    signup_sources = [("telegram_bot", 0.62), ("website", 0.38)]
    regular_plans = [("one_month", 0.58), ("three_months", 0.27), ("twelve_months", 0.15)]
    prospect_plans = [("one_month", 0.72), ("three_months", 0.20), ("twelve_months", 0.08)]
    prospect_windows = _month_windows(period_start, period_end - timedelta(days=10))
    prospect_weights = [0.55, 0.85, 1.45, 2.30, 0.70, 1.90]
    assert len(prospect_windows) == len(prospect_weights)

    for index in range(1, settings.regular_user_count + 1):
        user_id = f"usr_{index:06d}"
        subscription_id = f"sub_{index:06d}"
        signup_source = _weighted(rng, signup_sources)
        plan = _weighted(rng, regular_plans)
        registered_at = period_start - timedelta(days=rng.randint(120, 900))
        starts_at = registered_at + timedelta(days=rng.randint(1, 45))
        purchased_at = starts_at - timedelta(minutes=rng.randint(2, 45))
        issued_at = purchased_at + timedelta(minutes=rng.randint(1, 4))
        first_fetched_at = issued_at + timedelta(minutes=rng.randint(1, 40))
        acquisition_channel = _weighted(rng, acquisition_channels)

        rows["users"].append(
            {
                "user_id": user_id,
                "registered_at": _iso(registered_at),
                "acquisition_channel": acquisition_channel,
                "country": _weighted(rng, countries),
                "signup_source": signup_source,
                "is_internal": "false",
                "source_seed": settings.seed + index * 7919,
            }
        )
        rows["subscriptions"].append(
            {
                "subscription_id": subscription_id,
                "user_id": user_id,
                "sales_channel": signup_source,
                "plan": plan,
                "purchased_at": _iso(purchased_at),
                "starts_at": _iso(starts_at),
                "ends_at": "",
                "status": "active",
                "auto_renew": "true",
                "price_rub": PLAN_PRICES[plan],
                "currency": "RUB",
            }
        )
        rows["subscription_links"].append(
            {
                "subscription_link_id": f"lnk_{index:06d}",
                "subscription_id": subscription_id,
                "user_id": user_id,
                "issued_at": _iso(issued_at),
                "first_fetched_at": _iso(first_fetched_at),
                "last_fetched_at": _iso(period_end - timedelta(days=rng.randint(0, 21))),
                "fetch_count": rng.randint(12, 55),
                "client_name": "HAPP",
            }
        )

        payment_sequence = 1
        due_at = starts_at
        while due_at < period_start:
            due_at = _add_months(due_at, PLAN_MONTHS[plan])
        while due_at < period_end:
            _add_payment(
                rows,
                index,
                payment_sequence,
                subscription_id,
                user_id,
                due_at,
                PLAN_PRICES[plan],
                "renewal",
                signup_source,
            )
            payment_sequence += 1
            due_at = _add_months(due_at, PLAN_MONTHS[plan])

        session_sequence = 1
        for month_start, month_end in _month_windows(period_start, period_end):
            session_count = rng.randint(7, 18)
            session_times = sorted(
                _random_time(rng, month_start, month_end) for _ in range(session_count)
            )
            for monthly_sequence, session_at in enumerate(session_times):
                _add_session(
                    rows,
                    rng,
                    index,
                    session_sequence,
                    user_id,
                    subscription_id,
                    servers,
                    session_at,
                    force_success=monthly_sequence == 0,
                    failure_rate=0.045,
                )
                session_sequence += 1

    first_prospect_index = settings.regular_user_count + 1
    for offset in range(settings.prospect_user_count):
        index = first_prospect_index + offset
        user_id = f"usr_{index:06d}"
        signup_source = _weighted(rng, signup_sources)
        acquisition_channel = _weighted(rng, acquisition_channels)
        signup_window = rng.choices(prospect_windows, weights=prospect_weights, k=1)[0]
        registered_at = _random_time(rng, *signup_window, margin_minutes=0)
        is_internal = rng.random() < 0.012
        rows["users"].append(
            {
                "user_id": user_id,
                "registered_at": _iso(registered_at),
                "acquisition_channel": acquisition_channel,
                "country": _weighted(rng, countries),
                "signup_source": signup_source,
                "is_internal": str(is_internal).lower(),
                "source_seed": settings.seed + index * 7919,
            }
        )

        purchase_probability = 0.63 if signup_source == "telegram_bot" else 0.51
        if is_internal or rng.random() >= purchase_probability:
            continue

        subscription_id = f"sub_{index:06d}"
        plan = _weighted(rng, prospect_plans)
        purchased_at = registered_at + timedelta(hours=rng.uniform(0.1, 42))
        starts_at = purchased_at
        ends_at = _add_months(starts_at, PLAN_MONTHS[plan])
        status = "active" if ends_at >= period_end else "expired"
        rows["subscriptions"].append(
            {
                "subscription_id": subscription_id,
                "user_id": user_id,
                "sales_channel": signup_source,
                "plan": plan,
                "purchased_at": _iso(purchased_at),
                "starts_at": _iso(starts_at),
                "ends_at": _iso(ends_at),
                "status": status,
                "auto_renew": "false",
                "price_rub": PLAN_PRICES[plan],
                "currency": "RUB",
            }
        )
        _add_payment(
            rows,
            index,
            1,
            subscription_id,
            user_id,
            purchased_at,
            PLAN_PRICES[plan],
            "initial",
            signup_source,
        )

        issued_at = purchased_at + timedelta(minutes=rng.randint(1, 5))
        fetched = rng.random() < (0.93 if signup_source == "telegram_bot" else 0.86)
        first_fetched_at = issued_at + timedelta(hours=rng.uniform(0.02, 28)) if fetched else None
        active_until = min(ends_at, period_end)
        rows["subscription_links"].append(
            {
                "subscription_link_id": f"lnk_{index:06d}",
                "subscription_id": subscription_id,
                "user_id": user_id,
                "issued_at": _iso(issued_at),
                "first_fetched_at": _iso(first_fetched_at),
                "last_fetched_at": _iso(first_fetched_at),
                "fetch_count": rng.randint(1, 8) if fetched else 0,
                "client_name": "HAPP",
            }
        )
        if first_fetched_at is None or first_fetched_at >= active_until:
            continue

        engagement_score = rng.random() + (0.06 if signup_source == "telegram_bot" else 0)
        if engagement_score < 0.14:
            early_attempts = 0
        elif engagement_score < 0.34:
            early_attempts = rng.randint(1, 2)
        elif engagement_score < 0.72:
            early_attempts = rng.randint(3, 5)
        else:
            early_attempts = rng.randint(6, 10)

        early_days: list[int] = []
        if early_attempts >= 3:
            early_days.extend([0, rng.randint(1, 3)])
        while len(early_days) < early_attempts:
            early_days.append(rng.randint(0, 6))
        session_times = [
            first_fetched_at + timedelta(days=day, hours=rng.uniform(0.1, 12))
            for day in sorted(early_days)
        ]
        later_limit = max(0, (active_until - first_fetched_at).days // 5)
        later_attempts = rng.randint(0, min(18, later_limit)) if engagement_score >= 0.34 else 0
        for _ in range(later_attempts):
            later_start = first_fetched_at + timedelta(days=8)
            if later_start < active_until:
                session_times.append(_random_time(rng, later_start, active_until))

        for session_sequence, session_at in enumerate(sorted(session_times), start=1):
            if session_at >= active_until:
                continue
            _add_session(
                rows,
                rng,
                index,
                session_sequence,
                user_id,
                subscription_id,
                servers,
                session_at,
                failure_rate=0.095,
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
    parser = argparse.ArgumentParser(description="Generate deterministic HAPP VPN service data.")
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
        "regular_user_count": settings.regular_user_count,
        "prospect_user_count": settings.prospect_user_count,
        "counts": counts,
    }
    with (args.output_dir / "manifest.json").open("w", encoding="utf-8") as manifest_file:
        json.dump(manifest, manifest_file, ensure_ascii=False, indent=2, sort_keys=True)
        manifest_file.write("\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
