from __future__ import annotations

import csv
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as input_file:
        return list(csv.DictReader(input_file))


def _timestamp(value: str) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


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


def user_activation_records(input_dir: Path) -> list[dict[str, Any]]:
    """Calculate the canonical VPN 7-day activation contract from generated CSVs."""
    users = _read_csv(input_dir / "users.csv")
    devices_by_user: dict[str, list[dict[str, str]]] = {}
    for device in _read_csv(input_dir / "devices.csv"):
        devices_by_user.setdefault(device["user_id"], []).append(device)
    subscriptions = {row["user_id"]: row for row in _read_csv(input_dir / "subscriptions.csv")}
    assignments = {
        row["user_id"]: row["variant"]
        for row in _read_csv(input_dir / "experiment_assignments.csv")
        if row["experiment_id"] == "smart_location_onboarding_v1"
    }
    sessions_by_user: dict[str, list[dict[str, str]]] = {}
    for session in _read_csv(input_dir / "vpn_sessions.csv"):
        sessions_by_user.setdefault(session["user_id"], []).append(session)

    records: list[dict[str, Any]] = []
    for user in users:
        if user["is_internal"].lower() == "true":
            continue
        user_id = user["user_id"]
        registered_at = _timestamp(user["registered_at"])
        assert registered_at is not None
        deadline = registered_at + timedelta(days=7)
        installed_times = [
            timestamp
            for device in devices_by_user.get(user_id, [])
            if (timestamp := _timestamp(device["installed_at"])) is not None
        ]
        app_installed_at = min(installed_times, default=None)

        user_sessions = sessions_by_user.get(user_id, [])
        all_successful_times = sorted(
            started_at
            for session in user_sessions
            if session["connection_status"] == "success"
            and (started_at := _timestamp(session["started_at"])) is not None
        )
        all_attempts_7d: list[dict[str, str]] = []
        successful_7d: list[dict[str, str]] = []
        for session in user_sessions:
            started_at = _timestamp(session["started_at"])
            if started_at and registered_at <= started_at < deadline:
                all_attempts_7d.append(session)
                if session["connection_status"] == "success" and session["ended_at"]:
                    successful_7d.append(session)

        successful_times = sorted(
            _timestamp(session["started_at"])
            for session in successful_7d
            if _timestamp(session["started_at"]) is not None
        )
        first_success = all_successful_times[0] if all_successful_times else None
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

        failed_attempts = sum(
            session["connection_status"] == "failed" for session in all_attempts_7d
        )
        total_attempts = len(all_attempts_7d)
        activated = bool(
            app_installed_at
            and app_installed_at < deadline
            and len(successful_7d) >= 3
            and active_days >= 2
            and protected_minutes >= 30
        )
        subscription = subscriptions.get(user_id, {})
        records.append(
            {
                "user_id": user_id,
                "registered_at": registered_at,
                "acquisition_channel": user["acquisition_channel"],
                "country": user["country"],
                "signup_platform": user["signup_platform"],
                "plan": subscription.get("plan"),
                "subscription_status": subscription.get("status"),
                "converted_at": _timestamp(subscription.get("converted_at", "")),
                "app_installed_at": app_installed_at,
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
                "experiment_variant": assignments.get(user_id),
                "time_to_first_value_hours": (
                    (first_success - registered_at).total_seconds() / 3600
                    if first_success
                    else None
                ),
                "activated_7d": activated,
            }
        )
    return records
