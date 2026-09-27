from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .generator import TABLE_FIELDS
from .settings import project_root


@dataclass(frozen=True)
class CheckResult:
    check_name: str
    failure_count: int
    details: str = ""

    @property
    def status(self) -> str:
        return "PASS" if self.failure_count == 0 else "FAIL"


def _read_table(input_dir: Path, table_name: str) -> list[dict[str, str]]:
    path = input_dir / f"{table_name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Required dataset is missing: {path}")
    with path.open(encoding="utf-8", newline="") as input_file:
        reader = csv.DictReader(input_file)
        expected = TABLE_FIELDS[table_name]
        if reader.fieldnames != expected:
            raise ValueError(
                f"Unexpected columns in {path.name}: {reader.fieldnames}; expected {expected}"
            )
        return list(reader)


def _timestamp(value: str) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _unique_check(rows: list[dict[str, str]], key: str, name: str) -> CheckResult:
    values = [row[key] for row in rows]
    return CheckResult(name, len(values) - len(set(values)))


def validate_dataset(input_dir: Path) -> list[CheckResult]:
    tables = {name: _read_table(input_dir, name) for name in TABLE_FIELDS}
    users = {row["user_id"]: row for row in tables["users"]}
    devices = {row["device_id"]: row for row in tables["devices"]}
    servers = {row["server_id"]: row for row in tables["vpn_servers"]}

    results = [
        _unique_check(tables["users"], "user_id", "unique_user_id"),
        _unique_check(tables["devices"], "device_id", "unique_device_id"),
        _unique_check(tables["subscriptions"], "subscription_id", "unique_subscription_id"),
        _unique_check(tables["product_events"], "event_id", "unique_event_id"),
        _unique_check(tables["vpn_servers"], "server_id", "unique_server_id"),
        _unique_check(tables["vpn_sessions"], "vpn_session_id", "unique_vpn_session_id"),
    ]
    results.extend(
        [
            CheckResult(
                "devices_have_user",
                sum(row["user_id"] not in users for row in tables["devices"]),
            ),
            CheckResult(
                "events_have_user_and_device",
                sum(
                    row["user_id"] not in users
                    or (bool(row["device_id"]) and row["device_id"] not in devices)
                    for row in tables["product_events"]
                ),
            ),
            CheckResult(
                "sessions_have_parents",
                sum(
                    row["user_id"] not in users
                    or row["device_id"] not in devices
                    or row["server_id"] not in servers
                    for row in tables["vpn_sessions"]
                ),
            ),
        ]
    )

    chronology_failures = 0
    invalid_properties = 0
    for event in tables["product_events"]:
        registered_at = _timestamp(users[event["user_id"]]["registered_at"])
        occurred_at = _timestamp(event["occurred_at"])
        if registered_at and occurred_at and occurred_at < registered_at:
            chronology_failures += 1
        try:
            if not isinstance(json.loads(event["properties"]), dict):
                invalid_properties += 1
        except json.JSONDecodeError:
            invalid_properties += 1
    results.append(CheckResult("events_not_before_registration", chronology_failures))
    results.append(CheckResult("event_properties_are_json_objects", invalid_properties))

    device_chronology_failures = 0
    for device in tables["devices"]:
        registered_at = _timestamp(users[device["user_id"]]["registered_at"])
        installed_at = _timestamp(device["installed_at"])
        first_open_at = _timestamp(device["first_open_at"])
        if (
            not registered_at
            or not installed_at
            or installed_at < registered_at
            or (first_open_at and first_open_at < installed_at)
        ):
            device_chronology_failures += 1
    results.append(CheckResult("valid_device_chronology", device_chronology_failures))

    session_chronology_failures = 0
    session_consistency_failures = 0
    invalid_measures = 0
    invalid_status = 0
    for session in tables["vpn_sessions"]:
        started_at = _timestamp(session["started_at"])
        ended_at = _timestamp(session["ended_at"])
        device = devices.get(session["device_id"])
        registered_at = _timestamp(users[session["user_id"]]["registered_at"])
        installed_at = _timestamp(device["installed_at"]) if device else None
        if (
            not started_at
            or (ended_at and ended_at < started_at)
            or (registered_at and started_at < registered_at)
            or (installed_at and started_at < installed_at)
        ):
            session_chronology_failures += 1
        if device and device["user_id"] != session["user_id"]:
            session_consistency_failures += 1
        if (
            int(session["connection_time_ms"]) < 0
            or int(session["bytes_down"]) < 0
            or int(session["bytes_up"]) < 0
        ):
            invalid_measures += 1
        if (session["connection_status"] == "success") != bool(ended_at):
            invalid_status += 1
    results.append(CheckResult("valid_session_chronology", session_chronology_failures))
    results.append(CheckResult("session_user_device_consistency", session_consistency_failures))
    results.append(CheckResult("nonnegative_session_measures", invalid_measures))
    results.append(CheckResult("session_status_matches_end_time", invalid_status))

    assignments: dict[tuple[str, str], set[str]] = {}
    for row in tables["experiment_assignments"]:
        assignments.setdefault((row["experiment_id"], row["user_id"]), set()).add(row["variant"])
    results.append(
        CheckResult(
            "one_experiment_variant_per_user",
            sum(len(variants) > 1 for variants in assignments.values()),
        )
    )

    subscription_users = [row["user_id"] for row in tables["subscriptions"]]
    results.append(
        CheckResult(
            "one_subscription_per_user",
            abs(len(subscription_users) - len(users))
            + (len(subscription_users) - len(set(subscription_users))),
        )
    )
    results.append(
        CheckResult(
            "positive_server_capacity_and_cost",
            sum(
                int(row["capacity_mbps"]) <= 0 or float(row["hourly_cost_usd"]) <= 0
                for row in tables["vpn_servers"]
            ),
        )
    )
    return results


def _arguments(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate generated subscription VPN CSV files.")
    parser.add_argument("--input-dir", type=Path, default=project_root() / "data" / "generated")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = _arguments(argv)
    try:
        results = validate_dataset(args.input_dir)
    except (FileNotFoundError, ValueError, TypeError) as error:
        print(f"DATASET ERROR: {error}")
        return 2
    name_width = max(len(result.check_name) for result in results)
    print(f"{'check':<{name_width}}  failures  status")
    print(f"{'-' * name_width}  --------  ------")
    for result in results:
        print(f"{result.check_name:<{name_width}}  {result.failure_count:>8}  {result.status}")
    failure_count = sum(result.failure_count for result in results)
    print(f"\nTotal failures: {failure_count}")
    return 1 if failure_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
