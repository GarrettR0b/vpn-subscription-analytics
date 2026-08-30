# Validation log

Последний полный локальный прогон: 2026-08-30.

## Generated dataset

Профиль `small`, seed `20260830`:

| Table | Rows |
|---|---:|
| workspaces | 600 |
| users | 927 |
| subscriptions | 600 |
| product_events | 12,162 |
| tickets | 3,592 |
| ai_suggestions | 3,592 |
| experiment_assignments | 365 |

## Checks

- 17 Python data-quality checks: all `PASS`;
- 4 automated tests: all passed;
- Ruff lint: passed;
- notebook: 7 code cells executed, no error outputs;
- PostgreSQL container: healthy;
- 6 SQL data-quality checks: all `PASS`.

## Cross-layer reconciliation

`analytics.mart_workspace_activation` and the independent Python implementation returned
the same result:

| Metric | PostgreSQL | Python |
|---|---:|---:|
| eligible workspaces | 592 | 592 |
| activated workspaces | 191 | 191 |
| activation rate | 32.26% | 32.26% |
| control activation | 29.69% | 29.69% |
| treatment activation | 39.88% | 39.88% |

Все значения являются результатом симуляции и используются только для демонстрации метода.
