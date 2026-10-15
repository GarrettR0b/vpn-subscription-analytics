from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg

from vpn_analytics.metrics import (
    activation_experiment_records,
    monthly_business_records,
    subscriber_activation_records,
    subscriber_retention_records,
)


def _arguments() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Reconcile Python and PostgreSQL subscriber marts."
    )
    parser.add_argument("--input-dir", type=Path, default=project_root / "data" / "generated")
    parser.add_argument(
        "--database-url",
        default=os.environ.get(
            "DATABASE_URL",
            "postgresql://analytics:analytics@127.0.0.1:5432/vpn_analytics",
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    python_activation = {
        row["subscription_id"]: row for row in subscriber_activation_records(args.input_dir)
    }
    python_monthly = {row["month_start"]: row for row in monthly_business_records(args.input_dir)}
    python_retention = {
        (row["subscription_id"], row["activity_month"]): row
        for row in subscriber_retention_records(args.input_dir)
    }
    python_experiment = {
        row["subscription_id"]: row for row in activation_experiment_records(args.input_dir)
    }

    with psycopg.connect(args.database_url) as connection:
        database_activation = {
            row[0]: {
                "activated_7d": row[1],
                "successful_sessions_7d": row[2],
                "active_days_7d": row[3],
                "protected_minutes_7d": float(row[4]),
            }
            for row in connection.execute(
                "SELECT subscription_id, activated_7d, successful_sessions_7d, "
                "active_days_7d, protected_minutes_7d "
                "FROM analytics.mart_subscriber_activation"
            ).fetchall()
        }
        database_monthly = {
            row[0].isoformat(): {
                "monthly_active_paid_users": row[1],
                "regular_paid_users": row[2],
                "new_paid_users": row[3],
                "churned_users": row[4],
                "ending_paid_subscribers": row[5],
                "basic_active_subscribers": row[6],
                "pro_active_subscribers": row[7],
                "addon_mrr_rub": float(row[8]),
                "extra_device_slots": row[9],
                "normalized_mrr_rub": float(row[10]),
                "cash_revenue_rub": float(row[11]),
                "subscription_mrr_rub": float(row[12]),
                "traffic_gb": float(row[13]),
                "connection_failure_rate": float(row[14]) if row[14] is not None else None,
                "active_paid_subscribers": row[15],
            }
            for row in connection.execute(
                "SELECT month_start, monthly_active_paid_users, regular_paid_users, "
                "new_paid_users, churned_users, ending_paid_subscribers, "
                "basic_active_subscribers, pro_active_subscribers, addon_mrr_rub, extra_device_slots, "
                "normalized_mrr_rub, cash_revenue_rub, subscription_mrr_rub, traffic_gb, "
                "connection_failure_rate, active_paid_subscribers "
                "FROM analytics.mart_monthly_business"
            ).fetchall()
        }
        database_retention = {
            (row[0], row[1].isoformat()): {
                "month_number": row[2],
                "successful_sessions": row[3],
                "retained": row[4],
            }
            for row in connection.execute(
                "SELECT subscription_id, activity_month, month_number, "
                "successful_sessions, retained "
                "FROM analytics.mart_subscriber_retention"
            ).fetchall()
        }
        database_experiment = {
            row[0]: {"onboarding_variant": row[1], "activated_7d": row[2]}
            for row in connection.execute(
                "SELECT subscription_id, onboarding_variant, activated_7d "
                "FROM analytics.mart_activation_experiment"
            ).fetchall()
        }

    activation_keys = python_activation.keys() ^ database_activation.keys()
    activation_values = []
    for subscription_id in python_activation.keys() & database_activation.keys():
        python_row = python_activation[subscription_id]
        database_row = database_activation[subscription_id]
        if (
            python_row["activated_7d"] != database_row["activated_7d"]
            or python_row["successful_sessions_7d"] != database_row["successful_sessions_7d"]
            or python_row["active_days_7d"] != database_row["active_days_7d"]
            or abs(python_row["protected_minutes_7d"] - database_row["protected_minutes_7d"])
            > 0.001
        ):
            activation_values.append(subscription_id)

    monthly_keys = python_monthly.keys() ^ database_monthly.keys()
    monthly_values = []
    for month_start in python_monthly.keys() & database_monthly.keys():
        python_row = python_monthly[month_start]
        database_row = database_monthly[month_start]
        if (
            python_row["monthly_active_paid_users"] != database_row["monthly_active_paid_users"]
            or python_row["regular_paid_users"] != database_row["regular_paid_users"]
            or python_row["new_paid_users"] != database_row["new_paid_users"]
            or python_row["churned_users"] != database_row["churned_users"]
            or python_row["ending_paid_subscribers"] != database_row["ending_paid_subscribers"]
            or python_row["basic_active_subscribers"] != database_row["basic_active_subscribers"]
            or python_row["pro_active_subscribers"] != database_row["pro_active_subscribers"]
            or abs(python_row["addon_mrr_rub"] - database_row["addon_mrr_rub"]) > 0.01
            or python_row["extra_device_slots"] != database_row["extra_device_slots"]
            or abs(python_row["normalized_mrr_rub"] - database_row["normalized_mrr_rub"]) > 0.01
            or abs(python_row["cash_revenue_rub"] - database_row["cash_revenue_rub"]) > 0.01
            or abs(python_row["subscription_mrr_rub"] - database_row["subscription_mrr_rub"])
            > 0.01
            or abs(python_row["traffic_gb"] - database_row["traffic_gb"]) > 0.000001
            or (
                (python_row["connection_failure_rate"] is None)
                != (database_row["connection_failure_rate"] is None)
            )
            or (
                python_row["connection_failure_rate"] is not None
                and database_row["connection_failure_rate"] is not None
                and abs(
                    python_row["connection_failure_rate"] - database_row["connection_failure_rate"]
                ) > 0.000000001
            )
            or python_row["active_paid_subscribers"] != database_row["active_paid_subscribers"]
        ):
            monthly_values.append(month_start)

    retention_keys = python_retention.keys() ^ database_retention.keys()
    retention_values = []
    for key in python_retention.keys() & database_retention.keys():
        python_row = python_retention[key]
        database_row = database_retention[key]
        if (
            python_row["month_number"] != database_row["month_number"]
            or python_row["successful_sessions"] != database_row["successful_sessions"]
            or python_row["retained"] != database_row["retained"]
        ):
            retention_values.append(key)

    experiment_keys = python_experiment.keys() ^ database_experiment.keys()
    experiment_values = []
    for subscription_id in python_experiment.keys() & database_experiment.keys():
        python_row = python_experiment[subscription_id]
        database_row = database_experiment[subscription_id]
        if (
            python_row["onboarding_variant"] != database_row["onboarding_variant"]
            or python_row["activated_7d"] != database_row["activated_7d"]
        ):
            experiment_values.append(subscription_id)

    print(f"Activation key mismatches: {len(activation_keys)}")
    print(f"Activation metric mismatches: {len(activation_values)}")
    print(f"Monthly key mismatches: {len(monthly_keys)}")
    print(f"Monthly metric mismatches: {len(monthly_values)}")
    print(f"Retention key mismatches: {len(retention_keys)}")
    print(f"Retention metric mismatches: {len(retention_values)}")
    print(f"Experiment key mismatches: {len(experiment_keys)}")
    print(f"Experiment metric mismatches: {len(experiment_values)}")
    return (
        1
        if any(
            (
                activation_keys,
                activation_values,
                monthly_keys,
                monthly_values,
                retention_keys,
                retention_values,
                experiment_keys,
                experiment_values,
            )
        )
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
