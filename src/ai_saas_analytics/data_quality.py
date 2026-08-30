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
    workspaces = {row["workspace_id"]: row for row in tables["workspaces"]}
    users = {row["user_id"]: row for row in tables["users"]}
    tickets = {row["ticket_id"]: row for row in tables["tickets"]}
    workspace_created = {
        workspace_id: _timestamp(row["created_at"]) for workspace_id, row in workspaces.items()
    }

    results = [
        _unique_check(tables["workspaces"], "workspace_id", "unique_workspace_id"),
        _unique_check(tables["users"], "user_id", "unique_user_id"),
        _unique_check(tables["product_events"], "event_id", "unique_event_id"),
        _unique_check(tables["tickets"], "ticket_id", "unique_ticket_id"),
        _unique_check(tables["ai_suggestions"], "suggestion_id", "unique_suggestion_id"),
    ]

    results.extend(
        [
            CheckResult(
                "users_have_workspace",
                sum(row["workspace_id"] not in workspaces for row in tables["users"]),
            ),
            CheckResult(
                "events_have_workspace",
                sum(row["workspace_id"] not in workspaces for row in tables["product_events"]),
            ),
            CheckResult(
                "events_have_user",
                sum(
                    bool(row["user_id"]) and row["user_id"] not in users
                    for row in tables["product_events"]
                ),
            ),
            CheckResult(
                "tickets_have_workspace_and_user",
                sum(
                    row["workspace_id"] not in workspaces or row["created_by_user_id"] not in users
                    for row in tables["tickets"]
                ),
            ),
            CheckResult(
                "suggestions_have_parents",
                sum(
                    row["workspace_id"] not in workspaces
                    or row["user_id"] not in users
                    or row["ticket_id"] not in tickets
                    for row in tables["ai_suggestions"]
                ),
            ),
        ]
    )

    event_time_failures = 0
    invalid_properties = 0
    for event in tables["product_events"]:
        created_at = workspace_created.get(event["workspace_id"])
        occurred_at = _timestamp(event["occurred_at"])
        if created_at and occurred_at and occurred_at < created_at:
            event_time_failures += 1
        try:
            properties = json.loads(event["properties"])
            if not isinstance(properties, dict):
                invalid_properties += 1
        except json.JSONDecodeError:
            invalid_properties += 1
    results.append(CheckResult("events_not_before_workspace", event_time_failures))
    results.append(CheckResult("event_properties_are_json_objects", invalid_properties))

    suggestion_time_failures = 0
    suggestion_consistency_failures = 0
    negative_measure_failures = 0
    for suggestion in tables["ai_suggestions"]:
        created_at = _timestamp(suggestion["created_at"])
        accepted_at = _timestamp(suggestion["accepted_at"])
        if accepted_at and created_at and accepted_at < created_at:
            suggestion_time_failures += 1
        ticket = tickets.get(suggestion["ticket_id"])
        user = users.get(suggestion["user_id"])
        if ticket and (
            ticket["workspace_id"] != suggestion["workspace_id"]
            or (user and user["workspace_id"] != suggestion["workspace_id"])
        ):
            suggestion_consistency_failures += 1
        if (
            int(suggestion["latency_ms"]) < 0
            or int(suggestion["input_tokens"]) < 0
            or int(suggestion["output_tokens"]) < 0
            or float(suggestion["cost_usd"]) < 0
        ):
            negative_measure_failures += 1
    results.append(CheckResult("accepted_not_before_generated", suggestion_time_failures))
    results.append(CheckResult("suggestion_workspace_consistency", suggestion_consistency_failures))
    results.append(CheckResult("nonnegative_ai_measures", negative_measure_failures))

    assignments: dict[tuple[str, str], set[str]] = {}
    for row in tables["experiment_assignments"]:
        key = (row["experiment_id"], row["workspace_id"])
        assignments.setdefault(key, set()).add(row["variant"])
    results.append(
        CheckResult(
            "one_experiment_variant_per_workspace",
            sum(len(variants) > 1 for variants in assignments.values()),
        )
    )

    subscription_workspaces = [row["workspace_id"] for row in tables["subscriptions"]]
    results.append(
        CheckResult(
            "one_subscription_per_workspace",
            abs(len(subscription_workspaces) - len(workspaces))
            + (len(subscription_workspaces) - len(set(subscription_workspaces))),
        )
    )
    return results


def _arguments(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate generated AI SaaS CSV files.")
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
