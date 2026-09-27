from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg

from vpn_analytics.metrics import monthly_business_records, subscriber_activation_records


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
            "postgresql://analytics:analytics@localhost:5433/vpn_analytics",
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    python_activation = {
        row["subscription_id"]: row for row in subscriber_activation_records(args.input_dir)
    }
    python_monthly = {row["month_start"]: row for row in monthly_business_records(args.input_dir)}

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
                "normalized_mrr_rub": float(row[5]),
            }
            for row in connection.execute(
                "SELECT month_start, monthly_active_paid_users, regular_paid_users, "
                "new_paid_users, churned_users, normalized_mrr_rub "
                "FROM analytics.mart_monthly_business"
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
            or abs(python_row["normalized_mrr_rub"] - database_row["normalized_mrr_rub"]) > 0.01
        ):
            monthly_values.append(month_start)

    print(f"Activation key mismatches: {len(activation_keys)}")
    print(f"Activation metric mismatches: {len(activation_values)}")
    print(f"Monthly key mismatches: {len(monthly_keys)}")
    print(f"Monthly metric mismatches: {len(monthly_values)}")
    return 1 if activation_keys or activation_values or monthly_keys or monthly_values else 0


if __name__ == "__main__":
    raise SystemExit(main())
