from __future__ import annotations

import argparse
import os
from collections.abc import Iterable
from pathlib import Path

from .data_quality import validate_dataset
from .generator import TABLE_FIELDS
from .settings import project_root

LOAD_ORDER = (
    "dataset_periods",
    "users",
    "subscriptions",
    "subscription_links",
    "payments",
    "proxy_servers",
    "proxy_sessions",
)


def _arguments(argv: Iterable[str] | None = None) -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser(description="Load generated VPN CSV files into PostgreSQL.")
    parser.add_argument("--input-dir", type=Path, default=root / "data" / "generated")
    parser.add_argument(
        "--database-url",
        default=os.environ.get(
            "DATABASE_URL",
            "postgresql://analytics:analytics@localhost:5433/vpn_analytics",
        ),
    )
    parser.add_argument("--schema-sql", type=Path, default=root / "sql" / "ddl" / "001_schema.sql")
    parser.add_argument("--marts-dir", type=Path, default=root / "sql" / "marts")
    parser.add_argument(
        "--checks-sql",
        type=Path,
        default=root / "sql" / "checks" / "001_data_quality.sql",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = _arguments(argv)
    csv_results = validate_dataset(args.input_dir)
    if any(result.failure_count for result in csv_results):
        print("CSV validation failed; PostgreSQL load was not attempted.")
        for result in csv_results:
            if result.failure_count:
                print(f"- {result.check_name}: {result.failure_count}")
        return 1

    try:
        import psycopg
        from psycopg import sql
    except ImportError:
        print("psycopg is not installed. Run: python -m pip install -e .")
        return 2

    with psycopg.connect(args.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(args.schema_sql.read_text(encoding="utf-8"))
            for table_name in LOAD_ORDER:
                fields = TABLE_FIELDS[table_name]
                copy_statement = sql.SQL(
                    "COPY {}.{} ({}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE)"
                ).format(
                    sql.Identifier("core"),
                    sql.Identifier(table_name),
                    sql.SQL(", ").join(sql.Identifier(field) for field in fields),
                )
                with (
                    (args.input_dir / f"{table_name}.csv").open(
                        "r", encoding="utf-8", newline=""
                    ) as input_file,
                    cursor.copy(copy_statement) as copy,
                ):
                    while chunk := input_file.read(64 * 1024):
                        copy.write(chunk)
                print(f"Loaded core.{table_name}")
            for mart_path in sorted(args.marts_dir.glob("*.sql")):
                cursor.execute(mart_path.read_text(encoding="utf-8"))
                print(f"Created marts from {mart_path.name}")
            cursor.execute(args.checks_sql.read_text(encoding="utf-8"))
            results = cursor.fetchall()
            print("\nPostgreSQL checks")
            for check_name, failure_count, status in results:
                print(f"{check_name}: {failure_count} ({status})")
            if any(failure_count for _, failure_count, _ in results):
                connection.rollback()
                print("Load rolled back because a database check failed.")
                return 1
        connection.commit()
    print("PostgreSQL load and analytics mart refresh completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
