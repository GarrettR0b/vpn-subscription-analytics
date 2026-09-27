from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg

from vpn_analytics.metrics import user_activation_records


def _arguments() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Reconcile Python and PostgreSQL activation marts."
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
    python_rows = {row["user_id"]: row for row in user_activation_records(args.input_dir)}
    with psycopg.connect(args.database_url) as connection:
        database_rows = {
            row[0]: {
                "activated_7d": row[1],
                "successful_sessions_7d": row[2],
                "active_days_7d": row[3],
                "protected_minutes_7d": float(row[4]),
            }
            for row in connection.execute(
                "SELECT user_id, activated_7d, successful_sessions_7d, active_days_7d, "
                "protected_minutes_7d FROM analytics.mart_user_activation"
            ).fetchall()
        }

    key_mismatches = python_rows.keys() ^ database_rows.keys()
    value_mismatches: list[str] = []
    for user_id in python_rows.keys() & database_rows.keys():
        python_row = python_rows[user_id]
        database_row = database_rows[user_id]
        if (
            python_row["activated_7d"] != database_row["activated_7d"]
            or python_row["successful_sessions_7d"] != database_row["successful_sessions_7d"]
            or python_row["active_days_7d"] != database_row["active_days_7d"]
            or abs(python_row["protected_minutes_7d"] - database_row["protected_minutes_7d"])
            > 0.001
        ):
            value_mismatches.append(user_id)

    print(f"Python rows: {len(python_rows)}")
    print(f"PostgreSQL rows: {len(database_rows)}")
    print(f"Key mismatches: {len(key_mismatches)}")
    print(f"Metric mismatches: {len(value_mismatches)}")
    return 1 if key_mismatches or value_mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
