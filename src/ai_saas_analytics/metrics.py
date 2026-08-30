from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as input_file:
        return list(csv.DictReader(input_file))


def _timestamp(value: str) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def activation_records(input_dir: Path) -> list[dict[str, Any]]:
    """Calculate the canonical 7-day activation contract from generated CSVs."""
    workspaces = _read_csv(input_dir / "workspaces.csv")
    subscriptions = {row["workspace_id"]: row for row in _read_csv(input_dir / "subscriptions.csv")}
    assignments = {
        row["workspace_id"]: row["variant"]
        for row in _read_csv(input_dir / "experiment_assignments.csv")
        if row["experiment_id"] == "guided_onboarding_v1"
    }

    event_milestones: dict[str, dict[str, datetime]] = {}
    for event in _read_csv(input_dir / "product_events.csv"):
        milestone_name = {
            "knowledge_base_connected": "knowledge_base_connected_at",
            "teammate_invited": "teammate_invited_at",
        }.get(event["event_name"])
        if milestone_name:
            occurred_at = _timestamp(event["occurred_at"])
            milestones = event_milestones.setdefault(event["workspace_id"], {})
            if occurred_at and (
                milestone_name not in milestones or occurred_at < milestones[milestone_name]
            ):
                milestones[milestone_name] = occurred_at

    accepted: dict[str, list[datetime]] = {}
    for suggestion in _read_csv(input_dir / "ai_suggestions.csv"):
        accepted_at = _timestamp(suggestion["accepted_at"])
        if accepted_at:
            accepted.setdefault(suggestion["workspace_id"], []).append(accepted_at)

    records: list[dict[str, Any]] = []
    for workspace in workspaces:
        if workspace["is_internal"].lower() == "true":
            continue
        workspace_id = workspace["workspace_id"]
        created_at = _timestamp(workspace["created_at"])
        assert created_at is not None
        deadline = created_at + timedelta(days=7)
        milestones = event_milestones.get(workspace_id, {})
        kb_at = milestones.get("knowledge_base_connected_at")
        teammate_at = milestones.get("teammate_invited_at")
        accepted_times = sorted(accepted.get(workspace_id, []))
        accepted_7d = [value for value in accepted_times if value < deadline]
        first_accepted = accepted_times[0] if accepted_times else None
        activated = bool(
            kb_at
            and teammate_at
            and first_accepted
            and kb_at < deadline
            and teammate_at < deadline
            and len(accepted_7d) >= 3
            and first_accepted >= kb_at
            and first_accepted >= teammate_at
            and first_accepted < deadline
        )
        subscription = subscriptions.get(workspace_id, {})
        records.append(
            {
                "workspace_id": workspace_id,
                "created_at": created_at,
                "acquisition_channel": workspace["acquisition_channel"],
                "country": workspace["country"],
                "team_size_bucket": workspace["team_size_bucket"],
                "seat_count": int(workspace["seat_count"]),
                "plan": subscription.get("plan"),
                "subscription_status": subscription.get("status"),
                "knowledge_base_connected_at": kb_at,
                "teammate_invited_at": teammate_at,
                "first_accepted_suggestion_at": first_accepted,
                "accepted_suggestions_7d": len(accepted_7d),
                "experiment_variant": assignments.get(workspace_id),
                "time_to_first_value_hours": (
                    (first_accepted - created_at).total_seconds() / 3600 if first_accepted else None
                ),
                "activated_7d": activated,
            }
        )
    return records
