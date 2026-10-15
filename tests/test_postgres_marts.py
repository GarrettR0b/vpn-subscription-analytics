import os
from pathlib import Path

import psycopg
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="Set TEST_DATABASE_URL")
@pytest.mark.parametrize("period_end, months", [
    ("2026-06-15", 5), ("2026-07-01", 6), ("2026-01-20", 0),
])
def test_sql_retention_excludes_incomplete_months(period_end, months):
    # This SELECT uses fixture CTEs only. It never creates or changes database objects.
    sql = (ROOT / "sql/marts/003_mart_subscriber_retention.sql").read_text(encoding="utf-8")
    query = sql.split(" AS\n", 1)[1].split(";", 1)[0]
    query = query.replace("core.dataset_periods", "fixture_periods")
    query = query.replace("analytics.mart_subscriber_activation", "fixture_activation")
    query = query.replace("core.proxy_sessions", "fixture_sessions")
    fixtures = """WITH fixture_periods AS (SELECT %s::timestamptz AS period_end),
    fixture_activation AS (
        SELECT 'user' AS user_id, 'sub' AS subscription_id,
        TIMESTAMPTZ '2026-01-10 00:00:00+00' AS subscription_started_at,
        'website' AS sales_channel, 'basic' AS plan, false AS activated_7d
    ), fixture_sessions AS (
        SELECT 'sub' AS subscription_id, TIMESTAMPTZ '2026-01-11 00:00:00+00' AS started_at,
        'success' AS connection_status WHERE false
    ), """
    with psycopg.connect(
        os.environ["TEST_DATABASE_URL"], connect_timeout=5,
        options="-c default_transaction_read_only=on -c statement_timeout=10000 -c timezone=UTC",
    ) as connection:
        rows = connection.execute(fixtures + query.removeprefix("WITH "), (period_end,)).fetchall()
    assert len(rows) == months
    assert [row[4] for row in rows] == list(range(months))
    assert [row[-1] for row in rows] == ([True] + [False] * (months - 1) if months else [])
