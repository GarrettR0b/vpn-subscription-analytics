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
    "workspaces": [
        "workspace_id",
        "created_at",
        "acquisition_channel",
        "country",
        "team_size_bucket",
        "seat_count",
        "is_internal",
        "source_seed",
    ],
    "users": [
        "user_id",
        "workspace_id",
        "role",
        "created_at",
        "invited_at",
        "joined_at",
    ],
    "subscriptions": [
        "subscription_id",
        "workspace_id",
        "plan",
        "started_at",
        "trial_ends_at",
        "converted_at",
        "ended_at",
        "status",
        "monthly_price_usd",
    ],
    "product_events": [
        "event_id",
        "workspace_id",
        "user_id",
        "session_id",
        "occurred_at",
        "event_name",
        "properties",
    ],
    "tickets": [
        "ticket_id",
        "workspace_id",
        "created_by_user_id",
        "created_at",
        "resolved_at",
        "channel",
        "reopened_at",
        "csat",
    ],
    "ai_suggestions": [
        "suggestion_id",
        "ticket_id",
        "workspace_id",
        "user_id",
        "model_name",
        "created_at",
        "accepted_at",
        "edited",
        "latency_ms",
        "input_tokens",
        "output_tokens",
        "cost_usd",
    ],
    "experiment_assignments": [
        "experiment_id",
        "workspace_id",
        "variant",
        "assigned_at",
        "stratum",
    ],
}


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
    workspace_id: str,
    user_id: str,
    occurred_at: datetime,
    event_name: str,
    sequence: int,
    properties: dict[str, Any] | None = None,
) -> None:
    rows["product_events"].append(
        {
            "event_id": f"evt_{workspace_id[3:]}_{sequence:04d}",
            "workspace_id": workspace_id,
            "user_id": user_id,
            "session_id": f"ses_{workspace_id[3:]}_{sequence // 4:03d}",
            "occurred_at": _iso(occurred_at),
            "event_name": event_name,
            "properties": json.dumps(properties or {}, sort_keys=True, separators=(",", ":")),
        }
    )


def generate_rows(settings: GeneratorSettings) -> dict[str, list[dict[str, Any]]]:
    rng = random.Random(settings.seed)
    rows: dict[str, list[dict[str, Any]]] = {name: [] for name in TABLE_FIELDS}
    period_start = datetime.combine(settings.start_date, datetime.min.time(), tzinfo=UTC)
    observation_end = period_start + timedelta(days=settings.observation_days)

    channels = [
        ("organic", 0.31),
        ("content", 0.24),
        ("partner", 0.13),
        ("paid_search", 0.19),
        ("outbound", 0.13),
    ]
    countries = [
        ("RU", 0.42),
        ("KZ", 0.13),
        ("BY", 0.08),
        ("AM", 0.07),
        ("GE", 0.07),
        ("DE", 0.08),
        ("US", 0.08),
        ("Other", 0.07),
    ]
    sizes = [("1", 0.14), ("2-5", 0.37), ("6-20", 0.31), ("21-50", 0.13), ("51+", 0.05)]
    seat_ranges = {"1": (1, 1), "2-5": (2, 5), "6-20": (6, 20), "21-50": (21, 50), "51+": (51, 90)}

    for index in range(1, settings.workspace_count + 1):
        workspace_id = f"ws_{index:06d}"
        owner_id = f"usr_{index:06d}_00"
        created_at = period_start + timedelta(
            days=rng.randint(0, settings.observation_days - 15),
            seconds=rng.randint(8 * 3600, 20 * 3600),
        )
        team_size = _weighted(rng, sizes)
        seat_count = rng.randint(*seat_ranges[team_size])
        acquisition_channel = _weighted(rng, channels)
        country = _weighted(rng, countries)
        is_internal = rng.random() < 0.012
        workspace_seed = settings.seed + index * 7919

        rows["workspaces"].append(
            {
                "workspace_id": workspace_id,
                "created_at": _iso(created_at),
                "acquisition_channel": acquisition_channel,
                "country": country,
                "team_size_bucket": team_size,
                "seat_count": seat_count,
                "is_internal": str(is_internal).lower(),
                "source_seed": workspace_seed,
            }
        )
        rows["users"].append(
            {
                "user_id": owner_id,
                "workspace_id": workspace_id,
                "role": "owner",
                "created_at": _iso(created_at),
                "invited_at": "",
                "joined_at": _iso(created_at),
            }
        )

        event_sequence = 1
        _event(
            rows,
            workspace_id,
            owner_id,
            created_at,
            "signup_started",
            event_sequence,
            {"channel": acquisition_channel},
        )
        event_sequence += 1
        _event(
            rows,
            workspace_id,
            owner_id,
            created_at + timedelta(minutes=4),
            "workspace_created",
            event_sequence,
            {"seat_count": seat_count},
        )
        event_sequence += 1

        age_day = (created_at - period_start).days
        variant: str | None = None
        if age_day >= settings.experiment_start_day and not is_internal:
            variant = "treatment" if rng.random() < 0.5 else "control"
            rows["experiment_assignments"].append(
                {
                    "experiment_id": "guided_onboarding_v1",
                    "workspace_id": workspace_id,
                    "variant": variant,
                    "assigned_at": _iso(created_at + timedelta(minutes=5)),
                    "stratum": f"{acquisition_channel}:{team_size}",
                }
            )

        treatment_lift = 0.10 if variant == "treatment" else 0.0
        kb_probability = min(0.95, 0.69 + treatment_lift + (0.05 if team_size != "1" else -0.07))
        kb_connected_at: datetime | None = None
        if rng.random() < kb_probability:
            kb_delay_hours = rng.uniform(0.6, 42 if variant == "treatment" else 64)
            kb_connected_at = created_at + timedelta(hours=kb_delay_hours)
            _event(
                rows,
                workspace_id,
                owner_id,
                kb_connected_at,
                "knowledge_base_connected",
                event_sequence,
                {"source": _weighted(rng, [("notion", 0.4), ("url", 0.35), ("pdf", 0.25)])},
            )
            event_sequence += 1
        else:
            failure_at = created_at + timedelta(hours=rng.uniform(0.5, 24))
            _event(
                rows,
                workspace_id,
                owner_id,
                failure_at,
                "knowledge_base_connection_failed",
                event_sequence,
                {"reason": _weighted(rng, [("permissions", 0.55), ("format", 0.45)])},
            )
            event_sequence += 1

        teammate_probability = 0.0 if seat_count == 1 else min(0.94, 0.61 + treatment_lift)
        teammate_invited_at: datetime | None = None
        active_user_ids = [owner_id]
        if rng.random() < teammate_probability:
            teammate_invited_at = created_at + timedelta(
                hours=rng.uniform(1.0, 72 if variant == "treatment" else 96)
            )
            teammate_id = f"usr_{index:06d}_01"
            joined_at = teammate_invited_at + timedelta(hours=rng.uniform(0.2, 18))
            rows["users"].append(
                {
                    "user_id": teammate_id,
                    "workspace_id": workspace_id,
                    "role": "admin" if seat_count >= 10 else "agent",
                    "created_at": _iso(teammate_invited_at),
                    "invited_at": _iso(teammate_invited_at),
                    "joined_at": _iso(joined_at),
                }
            )
            active_user_ids.append(teammate_id)
            _event(
                rows,
                workspace_id,
                owner_id,
                teammate_invited_at,
                "teammate_invited",
                event_sequence,
                {"role": "agent"},
            )
            event_sequence += 1
            _event(
                rows, workspace_id, teammate_id, joined_at, "teammate_joined", event_sequence, {}
            )
            event_sequence += 1

        setup_complete_at = max(
            [value for value in (kb_connected_at, teammate_invited_at) if value is not None],
            default=created_at,
        )
        setup_complete = kb_connected_at is not None and teammate_invited_at is not None
        initial_ticket_count = rng.randint(3, 7) if setup_complete else rng.randint(0, 3)
        later_ticket_count = min(12, int(rng.expovariate(1 / (2.0 + min(seat_count, 20) / 5))))
        accepted_7d = 0

        for ticket_index in range(1, initial_ticket_count + later_ticket_count + 1):
            ticket_id = f"tkt_{index:06d}_{ticket_index:03d}"
            if ticket_index <= initial_ticket_count:
                base_at = setup_complete_at + timedelta(hours=1)
                ticket_at = base_at + timedelta(hours=rng.uniform(0.2, 60))
            else:
                ticket_at = created_at + timedelta(
                    days=rng.uniform(8, 35), hours=rng.uniform(0, 12)
                )
            if ticket_at >= observation_end:
                continue

            eligible_users = [owner_id]
            if len(active_user_ids) > 1:
                teammate_row = rows["users"][-1]
                if (
                    teammate_row["workspace_id"] == workspace_id
                    and datetime.fromisoformat(teammate_row["joined_at"]) <= ticket_at
                ):
                    eligible_users.append(active_user_ids[-1])
            acting_user = rng.choice(eligible_users)
            ticket_channel = _weighted(rng, [("email", 0.45), ("chat", 0.39), ("web", 0.16)])
            suggestion_at = ticket_at + timedelta(seconds=rng.randint(4, 45))
            latency_ms = _bounded_lognormal(rng, median=1200, sigma=0.65, low=180, high=9000)
            quality_probability = 0.76 - max(0, latency_ms - 1800) / 22000
            if not kb_connected_at:
                quality_probability -= 0.24
            accepted = rng.random() < max(0.18, min(0.90, quality_probability))
            accepted_at = (
                suggestion_at + timedelta(seconds=rng.randint(8, 180)) if accepted else None
            )
            edited = accepted and rng.random() < 0.31
            input_tokens = rng.randint(180, 1450)
            output_tokens = rng.randint(45, 360)
            cost_usd = input_tokens * 0.00000035 + output_tokens * 0.00000105
            resolved_at = (accepted_at or suggestion_at) + timedelta(minutes=rng.randint(2, 90))
            reopened = rng.random() < (0.08 if accepted else 0.22)
            reopened_at = resolved_at + timedelta(hours=rng.uniform(2, 48)) if reopened else None
            csat_mean = 4.35 if accepted and not reopened else 3.45
            csat = min(5.0, max(1.0, rng.gauss(csat_mean, 0.55)))

            rows["tickets"].append(
                {
                    "ticket_id": ticket_id,
                    "workspace_id": workspace_id,
                    "created_by_user_id": acting_user,
                    "created_at": _iso(ticket_at),
                    "resolved_at": _iso(resolved_at),
                    "channel": ticket_channel,
                    "reopened_at": _iso(reopened_at),
                    "csat": f"{csat:.2f}",
                }
            )
            suggestion_id = f"sug_{index:06d}_{ticket_index:03d}"
            rows["ai_suggestions"].append(
                {
                    "suggestion_id": suggestion_id,
                    "ticket_id": ticket_id,
                    "workspace_id": workspace_id,
                    "user_id": acting_user,
                    "model_name": "answerflow-small-v1",
                    "created_at": _iso(suggestion_at),
                    "accepted_at": _iso(accepted_at),
                    "edited": str(bool(edited)).lower(),
                    "latency_ms": latency_ms,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost_usd": f"{cost_usd:.6f}",
                }
            )
            _event(
                rows,
                workspace_id,
                acting_user,
                ticket_at,
                "ticket_created",
                event_sequence,
                {"channel": ticket_channel},
            )
            event_sequence += 1
            _event(
                rows,
                workspace_id,
                acting_user,
                suggestion_at,
                "ai_suggestion_generated",
                event_sequence,
                {"latency_ms": latency_ms, "model": "answerflow-small-v1"},
            )
            event_sequence += 1
            if accepted_at:
                _event(
                    rows,
                    workspace_id,
                    acting_user,
                    accepted_at,
                    "ai_suggestion_accepted",
                    event_sequence,
                    {"edited": bool(edited)},
                )
                event_sequence += 1
                if accepted_at < created_at + timedelta(days=7):
                    accepted_7d += 1

        activated_proxy = (
            kb_connected_at is not None
            and kb_connected_at < created_at + timedelta(days=7)
            and teammate_invited_at is not None
            and teammate_invited_at < created_at + timedelta(days=7)
            and accepted_7d >= 3
        )
        trial_ends_at = created_at + timedelta(days=14)
        channel_modifier = 0.06 if acquisition_channel in {"organic", "partner"} else 0.0
        conversion_probability = 0.27 + (0.44 if activated_proxy else 0.0) + channel_modifier
        converted = rng.random() < min(0.90, conversion_probability)
        converted_at = trial_ends_at - timedelta(hours=rng.uniform(3, 36)) if converted else None
        if converted_at and converted_at <= observation_end:
            status = "active"
        elif trial_ends_at > observation_end:
            status = "trial"
            converted_at = None
        else:
            status = "expired"
            converted_at = None
        plan = _weighted(rng, [("starter", 0.52), ("growth", 0.36), ("business", 0.12)])
        base_price = {"starter": 49, "growth": 149, "business": 399}[plan]
        rows["subscriptions"].append(
            {
                "subscription_id": f"sub_{index:06d}",
                "workspace_id": workspace_id,
                "plan": plan,
                "started_at": _iso(created_at),
                "trial_ends_at": _iso(trial_ends_at),
                "converted_at": _iso(converted_at),
                "ended_at": "",
                "status": status,
                "monthly_price_usd": f"{base_price:.2f}",
            }
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
        output_path = output_dir / f"{table_name}.csv"
        with output_path.open("w", newline="", encoding="utf-8") as output_file:
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
    parser = argparse.ArgumentParser(description="Generate deterministic synthetic AI SaaS data.")
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
