from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

import psycopg
from psycopg import sql

MARTS = {
    "mart_monthly_business": ("month_start",),
    "mart_subscriber_activation": ("user_id", "subscription_id"),
    "mart_subscriber_retention": ("cohort_month", "user_id", "activity_month"),
    "mart_activation_experiment": ("user_id", "subscription_id"),
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Export PostgreSQL marts for Yandex DataLens.")
    parser.add_argument(
        "--database-url",
        default=os.environ.get(
            "DATABASE_URL",
            "postgresql://analytics:analytics@127.0.0.1:5432/vpn_analytics",
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "datalens",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    with psycopg.connect(args.database_url) as connection:
        for mart, order_by in MARTS.items():
            query = sql.SQL("SELECT * FROM {}.{} ORDER BY {}").format(
                sql.Identifier("analytics"),
                sql.Identifier(mart),
                sql.SQL(", ").join(sql.Identifier(column) for column in order_by),
            )
            with connection.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
                if not rows:
                    raise RuntimeError(f"analytics.{mart} is empty")
                output_path = args.output_dir / f"{mart}.csv"
                with output_path.open("w", encoding="utf-8-sig", newline="") as output_file:
                    writer = csv.writer(output_file)
                    writer.writerow(column.name for column in cursor.description)
                    writer.writerows(rows)
                print(f"{output_path}: {len(rows)} rows")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
