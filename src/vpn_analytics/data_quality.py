from __future__ import annotations

import argparse
import csv
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .generator import TABLE_FIELDS
from .metrics import monthly_business_records
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
    subscriptions = {row["subscription_id"]: row for row in tables["subscriptions"]}
    servers = {row["server_id"]: row for row in tables["proxy_servers"]}
    periods = tables["dataset_periods"]

    results = [
        CheckResult("one_dataset_period", abs(len(periods) - 1)),
        _unique_check(tables["users"], "user_id", "unique_user_id"),
        _unique_check(tables["subscriptions"], "subscription_id", "unique_subscription_id"),
        _unique_check(
            tables["subscription_links"],
            "subscription_link_id",
            "unique_subscription_link_id",
        ),
        _unique_check(tables["payments"], "payment_id", "unique_payment_id"),
        _unique_check(tables["proxy_servers"], "server_id", "unique_server_id"),
        _unique_check(tables["proxy_sessions"], "proxy_session_id", "unique_proxy_session_id"),
    ]

    subscription_users = [row["user_id"] for row in tables["subscriptions"]]
    link_subscriptions = [row["subscription_id"] for row in tables["subscription_links"]]
    results.extend(
        [
            CheckResult(
                "subscriptions_have_users",
                sum(row["user_id"] not in users for row in tables["subscriptions"]),
            ),
            CheckResult(
                "one_subscription_per_user",
                len(subscription_users) - len(set(subscription_users)),
            ),
            CheckResult(
                "one_link_per_subscription",
                abs(len(link_subscriptions) - len(subscriptions))
                + (len(link_subscriptions) - len(set(link_subscriptions))),
            ),
            CheckResult(
                "links_have_matching_subscription_and_user",
                sum(
                    (subscription := subscriptions.get(row["subscription_id"])) is None
                    or subscription["user_id"] != row["user_id"]
                    for row in tables["subscription_links"]
                ),
            ),
            CheckResult(
                "payments_have_matching_subscription_and_user",
                sum(
                    (subscription := subscriptions.get(row["subscription_id"])) is None
                    or subscription["user_id"] != row["user_id"]
                    for row in tables["payments"]
                ),
            ),
            CheckResult(
                "sessions_have_matching_parents",
                sum(
                    row["user_id"] not in users
                    or row["server_id"] not in servers
                    or (subscription := subscriptions.get(row["subscription_id"])) is None
                    or subscription["user_id"] != row["user_id"]
                    for row in tables["proxy_sessions"]
                ),
            ),
        ]
    )

    subscription_chronology_failures = 0
    invalid_subscription_status = 0
    period_end = _timestamp(periods[0]["period_end"]) if periods else None
    for subscription in tables["subscriptions"]:
        user = users.get(subscription["user_id"])
        registered_at = _timestamp(user["registered_at"]) if user else None
        purchased_at = _timestamp(subscription["purchased_at"])
        starts_at = _timestamp(subscription["starts_at"])
        ends_at = _timestamp(subscription["ends_at"])
        if (
            not registered_at
            or not purchased_at
            or not starts_at
            or purchased_at < registered_at
            or starts_at < purchased_at
            or (ends_at and ends_at < starts_at)
        ):
            subscription_chronology_failures += 1
        expected_status = "active" if not ends_at or ends_at >= period_end else "expired"
        invalid_subscription_status += subscription["status"] != expected_status
    results.append(CheckResult("valid_subscription_chronology", subscription_chronology_failures))
    results.append(CheckResult("subscription_status_matches_period", invalid_subscription_status))

    link_chronology_failures = 0
    invalid_happ_client = 0
    for link in tables["subscription_links"]:
        subscription = subscriptions.get(link["subscription_id"])
        issued_at = _timestamp(link["issued_at"])
        first_fetched_at = _timestamp(link["first_fetched_at"])
        last_fetched_at = _timestamp(link["last_fetched_at"])
        purchased_at = _timestamp(subscription["purchased_at"]) if subscription else None
        if (
            not issued_at
            or (purchased_at and issued_at < purchased_at)
            or (first_fetched_at and first_fetched_at < issued_at)
            or (last_fetched_at and first_fetched_at and last_fetched_at < first_fetched_at)
            or (bool(first_fetched_at) != (int(link["fetch_count"]) > 0))
        ):
            link_chronology_failures += 1
        invalid_happ_client += link["client_name"] != "HAPP"
    results.append(CheckResult("valid_subscription_link_chronology", link_chronology_failures))
    results.append(CheckResult("subscription_client_is_happ", invalid_happ_client))

    payment_chronology_failures = 0
    for payment in tables["payments"]:
        subscription = subscriptions.get(payment["subscription_id"])
        paid_at = _timestamp(payment["paid_at"])
        purchased_at = _timestamp(subscription["purchased_at"]) if subscription else None
        if not paid_at or (purchased_at and paid_at < purchased_at):
            payment_chronology_failures += 1
    results.append(CheckResult("valid_payment_chronology", payment_chronology_failures))

    session_chronology_failures = 0
    invalid_measures = 0
    invalid_status = 0
    for session in tables["proxy_sessions"]:
        subscription = subscriptions.get(session["subscription_id"])
        started_at = _timestamp(session["started_at"])
        ended_at = _timestamp(session["ended_at"])
        subscription_start = _timestamp(subscription["starts_at"]) if subscription else None
        subscription_end = _timestamp(subscription["ends_at"]) if subscription else None
        if (
            not started_at
            or (ended_at and ended_at < started_at)
            or (subscription_start and started_at < subscription_start)
            or (subscription_end and started_at >= subscription_end)
        ):
            session_chronology_failures += 1
        if (
            int(session["connection_time_ms"]) < 0
            or int(session["bytes_down"]) < 0
            or int(session["bytes_up"]) < 0
        ):
            invalid_measures += 1
        if (session["connection_status"] == "success") != bool(ended_at):
            invalid_status += 1
    results.append(CheckResult("valid_proxy_session_chronology", session_chronology_failures))
    results.append(CheckResult("nonnegative_session_measures", invalid_measures))
    results.append(CheckResult("session_status_matches_end_time", invalid_status))
    results.append(
        CheckResult(
            "positive_server_capacity_and_cost",
            sum(
                int(row["capacity_mbps"]) <= 0 or float(row["monthly_cost_rub"]) <= 0
                for row in tables["proxy_servers"]
            ),
        )
    )

    if periods:
        target = int(periods[0]["regular_user_target"])
        monthly = monthly_business_records(input_dir)
        results.append(
            CheckResult(
                "regular_paid_users_match_target",
                sum(row["regular_paid_users"] != target for row in monthly),
                f"target={target}",
            )
        )
    return results


def _arguments(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate generated HAPP VPN service CSV files.")
    parser.add_argument("--input-dir", type=Path, default=project_root() / "data" / "generated")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = _arguments(argv)
    try:
        results = validate_dataset(args.input_dir)
    except (FileNotFoundError, ValueError, TypeError, KeyError) as error:
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
