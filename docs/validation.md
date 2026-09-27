# Validation log

Последний полный локальный прогон: 2026-09-27.

## Generated dataset

Профиль `small`, seed `20260830`, период январь–июнь 2026:

| Table | Rows |
|---|---:|
| dataset_periods | 1 |
| users | 800 |
| subscriptions | 649 |
| subscription_links | 649 |
| payments | 2,056 |
| proxy_servers | 18 |
| proxy_sessions | 33,819 |

## Monthly dynamics

| Month | New paid | Churned | Active paid | Monthly active | Stable core |
|---|---:|---:|---:|---:|---:|
| Jan | 12 | 0 | 447 | 442 | 435 |
| Feb | 21 | 9 | 468 | 455 | 435 |
| Mar | 40 | 16 | 499 | 474 | 435 |
| Apr | 63 | 33 | 546 | 508 | 435 |
| May | 25 | 52 | 538 | 489 | 435 |
| Jun | 53 | 24 | 539 | 507 | 435 |

Неравномерность притока задана детерминированными сезонными весами: спокойный старт,
апрельский всплеск, майский откат и июньский подъём. Изменения остаются соразмерными базе.

## Activation

| Metric | Result |
|---|---:|
| eligible new subscriptions | 214 |
| activated in 7 days | 118 |
| activation rate | 55.14% |
| link fetched in HAPP | 89.25% |
| Telegram-bot activation | 58.65% |
| website activation | 49.38% |

## Checks

- 23 Python data-quality checks: all `PASS`;
- 4 automated tests: all passed;
- Ruff lint and format: passed;
- PostgreSQL container: healthy;
- 9 SQL data-quality checks: all `PASS`;
- Python ↔ PostgreSQL reconciliation: 0 key and 0 metric mismatches;
- notebook: executed top-to-bottom with no error outputs.

Все значения являются результатом симуляции и демонстрируют метод, а не реальные
показатели компании.
