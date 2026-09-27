# Validation log

Последний полный локальный прогон: 2026-08-30.

## Generated dataset

Профиль `small`, seed `20260830`:

| Table | Rows |
|---|---:|
| users | 800 |
| devices | 727 |
| subscriptions | 800 |
| product_events | 10,185 |
| vpn_servers | 24 |
| vpn_sessions | 5,305 |
| experiment_assignments | 501 |

## Checks

- 19 Python data-quality checks: all `PASS`;
- 4 automated tests: all passed;
- Ruff lint and format: passed;
- notebook: 7 code cells executed, no error outputs;
- PostgreSQL container: healthy;
- 8 SQL data-quality checks: all `PASS`;
- row-level Python ↔ PostgreSQL reconciliation: 0 key and 0 metric mismatches.

## Cross-layer results

| Metric | PostgreSQL | Python |
|---|---:|---:|
| eligible users | 791 | 791 |
| activated users | 438 | 438 |
| activation rate | 55.37% | 55.37% |
| control activation | 53.23% | 53.23% |
| treatment activation | 65.97% | 65.97% |
| activated paid conversion | 71.00% | 71.00% |
| non-activated paid conversion | 16.15% | 16.15% |

Все значения являются результатом симуляции и используются только для демонстрации метода.
