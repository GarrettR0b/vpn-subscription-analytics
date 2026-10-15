from unittest.mock import MagicMock

import psycopg

from vpn_analytics import loader
from vpn_analytics.generator import TABLE_FIELDS


def test_load_requires_explicit_reset_before_reading_data(monkeypatch):
    validate = MagicMock()
    connect = MagicMock()
    monkeypatch.setattr(loader, "validate_dataset", validate)
    monkeypatch.setattr(psycopg, "connect", connect)
    assert loader.main([]) == 2
    validate.assert_not_called()
    connect.assert_not_called()


def test_wrong_database_is_refused_before_ddl(monkeypatch):
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = ("other_database",)
    monkeypatch.setattr(loader, "validate_dataset", lambda _: [])
    monkeypatch.setattr(psycopg, "connect", lambda _: connection)
    connection.__enter__.return_value = connection
    assert loader.main(["--reset-database", "vpn_analytics"]) == 2
    cursor.execute.assert_called_once_with("SELECT current_database()")
    connection.commit.assert_not_called()


def test_matching_reset_preserves_transactional_load(monkeypatch, tmp_path):
    connection = MagicMock()
    connection.__enter__.return_value = connection
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = ("vpn_analytics",)
    cursor.fetchall.return_value = [("check", 0, "PASS")]
    for name, fields in TABLE_FIELDS.items():
        (tmp_path / f"{name}.csv").write_text(",".join(fields) + "\n", encoding="utf-8")
    monkeypatch.setattr(loader, "validate_dataset", lambda _: [])
    monkeypatch.setattr(psycopg, "connect", lambda _: connection)
    assert loader.main([
        "--reset-database", "vpn_analytics", "--input-dir", str(tmp_path),
    ]) == 0
    statements = [call.args[0] for call in cursor.execute.call_args_list]
    assert statements[:2] == ["SELECT current_database()", "SET LOCAL TIME ZONE 'UTC'"]
    assert statements[2].startswith("DROP SCHEMA")
    assert cursor.copy.call_count == len(TABLE_FIELDS)
    connection.commit.assert_called_once()
