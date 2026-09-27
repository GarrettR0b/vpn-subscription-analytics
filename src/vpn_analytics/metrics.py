from __future__ import annotations

import csv
import math
from calendar import monthrange
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .generator import PLAN_MONTHS


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as input_file:
        return list(csv.DictReader(input_file))


def _timestamp(value: str) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _add_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _percentile_cont(values: list[int], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return float(ordered[lower_index])
    fraction = position - lower_index
    return ordered[lower_index] + (ordered[upper_index] - ordered[lower_index]) * fraction


def subscriber_activation_records(input_dir: Path) -> list[dict[str, Any]]:
    """Calculate post-purchase activation for subscriptions configured in HAPP."""
    period = _read_csv(input_dir / "dataset_periods.csv")[0]
    period_start = _timestamp(period["period_start"])
    period_end = _timestamp(period["period_end"])
    assert period_start is not None and period_end is not None

    users = {row["user_id"]: row for row in _read_csv(input_dir / "users.csv")}
    links = {row["subscription_id"]: row for row in _read_csv(input_dir / "subscription_links.csv")}
    sessions_by_subscription: dict[str, list[dict[str, str]]] = {}
    for session in _read_csv(input_dir / "proxy_sessions.csv"):
        sessions_by_subscription.setdefault(session["subscription_id"], []).append(session)

    records: list[dict[str, Any]] = []
    for subscription in _read_csv(input_dir / "subscriptions.csv"):
        user = users[subscription["user_id"]]
        starts_at = _timestamp(subscription["starts_at"])
        assert starts_at is not None
        if (
            user["is_internal"].lower() == "true"
            or starts_at < period_start
            or starts_at + timedelta(days=7) > period_end
        ):
            continue

        deadline = starts_at + timedelta(days=7)
        subscription_sessions = sessions_by_subscription.get(subscription["subscription_id"], [])
        attempts_7d: list[dict[str, str]] = []
        successful_7d: list[dict[str, str]] = []
        for session in subscription_sessions:
            started_at = _timestamp(session["started_at"])
            if started_at and starts_at <= started_at < deadline:
                attempts_7d.append(session)
                if session["connection_status"] == "success" and session["ended_at"]:
                    successful_7d.append(session)

        successful_times = [
            started_at
            for session in successful_7d
            if (started_at := _timestamp(session["started_at"])) is not None
        ]
        first_success = min(successful_times, default=None)
        active_days = len({started_at.date() for started_at in successful_times})
        protected_minutes = 0.0
        traffic_bytes = 0
        connection_times: list[int] = []
        forced_disconnects = 0
        for session in successful_7d:
            started_at = _timestamp(session["started_at"])
            ended_at = _timestamp(session["ended_at"])
            if started_at and ended_at:
                protected_minutes += (ended_at - started_at).total_seconds() / 60
            traffic_bytes += int(session["bytes_down"]) + int(session["bytes_up"])
            connection_times.append(int(session["connection_time_ms"]))
            forced_disconnects += session["disconnect_reason"] == "network_lost"

        link = links[subscription["subscription_id"]]
        first_link_fetched_at = _timestamp(link["first_fetched_at"])
        failed_attempts = sum(session["connection_status"] == "failed" for session in attempts_7d)
        total_attempts = len(attempts_7d)
        activated = bool(
            first_link_fetched_at
            and first_link_fetched_at < deadline
            and len(successful_7d) >= 3
            and active_days >= 2
            and protected_minutes >= 30
        )
        records.append(
            {
                "user_id": user["user_id"],
                "subscription_id": subscription["subscription_id"],
                "registered_at": _timestamp(user["registered_at"]),
                "acquisition_channel": user["acquisition_channel"],
                "country": user["country"],
                "signup_source": user["signup_source"],
                "sales_channel": subscription["sales_channel"],
                "plan": subscription["plan"],
                "price_rub": float(subscription["price_rub"]),
                "purchased_at": _timestamp(subscription["purchased_at"]),
                "subscription_started_at": starts_at,
                "link_issued_at": _timestamp(link["issued_at"]),
                "first_link_fetched_at": first_link_fetched_at,
                "first_successful_connection_at": first_success,
                "successful_sessions_7d": len(successful_7d),
                "active_days_7d": active_days,
                "protected_minutes_7d": protected_minutes,
                "traffic_gb_7d": traffic_bytes / 1_000_000_000,
                "failed_attempts_7d": failed_attempts,
                "total_attempts_7d": total_attempts,
                "failure_rate_7d": failed_attempts / total_attempts if total_attempts else None,
                "p95_connection_time_ms": _percentile_cont(connection_times, 0.95),
                "forced_disconnect_rate_7d": (
                    forced_disconnects / len(successful_7d) if successful_7d else None
                ),
                "time_to_first_value_hours": (
                    (first_success - starts_at).total_seconds() / 3600 if first_success else None
                ),
                "activated_7d": activated,
            }
        )
    return records


def monthly_business_records(input_dir: Path) -> list[dict[str, Any]]:
    """Calculate complete-month subscriber, revenue and proxy usage metrics."""
    period = _read_csv(input_dir / "dataset_periods.csv")[0]
    period_start = _timestamp(period["period_start"])
    period_end = _timestamp(period["period_end"])
    assert period_start is not None and period_end is not None

    users = {row["user_id"]: row for row in _read_csv(input_dir / "users.csv")}
    subscriptions = [
        row
        for row in _read_csv(input_dir / "subscriptions.csv")
        if users[row["user_id"]]["is_internal"].lower() != "true"
    ]
    payments = _read_csv(input_dir / "payments.csv")
    sessions = _read_csv(input_dir / "proxy_sessions.csv")
    regular_users = {
        row["user_id"]
        for row in subscriptions
        if (_timestamp(row["starts_at"]) or period_start) < period_start
        and ((ends_at := _timestamp(row["ends_at"])) is None or ends_at >= period_end)
    }

    records: list[dict[str, Any]] = []
    month_start = period_start
    while month_start < period_end:
        month_end = _add_months(month_start, 1)
        if month_end > period_end:
            break

        active_subscriptions = [
            row
            for row in subscriptions
            if (_timestamp(row["starts_at"]) or period_end) < month_end
            and ((ends_at := _timestamp(row["ends_at"])) is None or ends_at >= month_start)
        ]
        active_at_month_end = [
            row
            for row in subscriptions
            if (_timestamp(row["starts_at"]) or period_end) < month_end
            and ((ends_at := _timestamp(row["ends_at"])) is None or ends_at >= month_end)
        ]
        monthly_sessions = [
            row
            for row in sessions
            if month_start <= (_timestamp(row["started_at"]) or period_end) < month_end
        ]
        successful_users = {
            row["user_id"] for row in monthly_sessions if row["connection_status"] == "success"
        }
        active_user_ids = {row["user_id"] for row in active_subscriptions}
        failed_sessions = sum(row["connection_status"] == "failed" for row in monthly_sessions)
        traffic_bytes = sum(
            int(row["bytes_down"]) + int(row["bytes_up"])
            for row in monthly_sessions
            if row["connection_status"] == "success"
        )
        records.append(
            {
                "month_start": month_start.date().isoformat(),
                "active_paid_subscribers": len(active_user_ids),
                "monthly_active_paid_users": len(successful_users & active_user_ids),
                "regular_paid_users": len(successful_users & regular_users),
                "new_paid_users": sum(
                    month_start <= (_timestamp(row["starts_at"]) or period_end) < month_end
                    for row in subscriptions
                ),
                "churned_users": sum(
                    month_start <= ends_at < month_end
                    for row in subscriptions
                    if (ends_at := _timestamp(row["ends_at"])) is not None
                ),
                "cash_revenue_rub": sum(
                    float(row["amount_rub"])
                    for row in payments
                    if row["payment_status"] == "succeeded"
                    and month_start <= (_timestamp(row["paid_at"]) or period_end) < month_end
                ),
                "normalized_mrr_rub": sum(
                    float(row["price_rub"]) / PLAN_MONTHS[row["plan"]]
                    for row in active_at_month_end
                ),
                "connection_failure_rate": (
                    failed_sessions / len(monthly_sessions) if monthly_sessions else None
                ),
                "traffic_gb": traffic_bytes / 1_000_000_000,
            }
        )
        month_start = month_end
    return records
