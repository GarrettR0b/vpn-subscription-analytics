from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import reconcile_postgres as reconcile


@pytest.mark.parametrize("changed", [
    None, "cash_revenue_rub", "subscription_mrr_rub", "traffic_gb",
    "connection_failure_rate", "active_paid_subscribers",
])
def test_monthly_reconciliation_checks_report_metrics(monkeypatch, tmp_path, changed):
    database_row = {
        "month_start": date(2026, 1, 1), "monthly_active_paid_users": 1,
        "regular_paid_users": 1, "new_paid_users": 1, "churned_users": 0,
        "ending_paid_subscribers": 1, "basic_active_subscribers": 1,
        "pro_active_subscribers": 0, "addon_mrr_rub": 0, "extra_device_slots": 0,
        "normalized_mrr_rub": 130, "cash_revenue_rub": 130,
        "subscription_mrr_rub": 130, "traffic_gb": 0, "connection_failure_rate": None,
        "active_paid_subscribers": 1,
    }
    python_row = {**database_row, "month_start": "2026-01-01"}
    if changed:
        python_row[changed] = 0.5 if changed == "connection_failure_rate" else 999
    connection = MagicMock()
    connection.__enter__.return_value = connection

    def execute(query):
        result = MagicMock()
        if "mart_monthly_business" in query:
            columns = query.split("FROM")[0].removeprefix("SELECT ").strip().split(", ")
            result.fetchall.return_value = [tuple(database_row[field] for field in columns)]
        else:
            result.fetchall.return_value = []
        return result

    connection.execute.side_effect = execute
    monkeypatch.setattr(reconcile.psycopg, "connect", lambda _: connection)
    monkeypatch.setattr(reconcile, "_arguments", lambda: SimpleNamespace(
        input_dir=tmp_path, database_url="mock",
    ))
    for function in ("subscriber_activation_records", "subscriber_retention_records",
                     "activation_experiment_records"):
        monkeypatch.setattr(reconcile, function, lambda _: [])
    monkeypatch.setattr(reconcile, "monthly_business_records", lambda _: [python_row])
    assert reconcile.main() == (1 if changed else 0)
