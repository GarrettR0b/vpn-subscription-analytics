# Validation log

Последний полный локальный прогон: 2026-09-27.

## Generated dataset

Профиль `small`, seed `20260830`, период январь–июнь 2026:

| Table | Rows |
|---|---:|
| dataset_periods | 1 |
| users | 800 |
| subscriptions | 652 |
| subscription_links | 652 |
| payments | 3,033 |
| proxy_servers | 18 |
| proxy_sessions | 34,701 |

## Monthly dynamics

| Month | New paid | Churned | Active paid | Monthly active | Stable core |
|---|---:|---:|---:|---:|---:|
| Jan | 15 | 0 | 450 | 450 | 435 |
| Feb | 13 | 4 | 459 | 457 | 435 |
| Mar | 43 | 7 | 495 | 482 | 435 |
| Apr | 64 | 21 | 538 | 513 | 435 |
| May | 25 | 29 | 534 | 523 | 435 |
| Jun | 57 | 34 | 557 | 546 | 435 |

Неравномерность притока задана детерминированными сезонными весами: спокойный старт,
апрельский всплеск, майский откат и июньский подъём. Изменения остаются соразмерными базе.

## Activation

| Metric | Result |
|---|---:|
| eligible new subscriptions | 217 |
| activated in 7 days | 140 |
| activation rate | 64.52% |
| link fetched in HAPP | 91.71% |
| Telegram-bot activation | 67.50% |
| website activation | 56.14% |

## Retention

| Month age | Eligible | Returned | Usage retention |
|---|---:|---:|---:|
| M1 | 160 | 90 | 56.25% |
| M2 | 135 | 65 | 48.15% |
| M3 | 71 | 14 | 19.72% |
| M4 | 28 | 5 | 17.86% |
| M5 | 15 | 3 | 20.00% |

M1 у активировавшихся — 66.99%, у не активировавшихся — 36.84%. Это описательная
сегментация, не оценка причинного эффекта.

## Experiment

| Metric | Result |
|---|---:|
| control / treatment | 109 / 108 |
| control activation | 61.47% |
| treatment activation | 67.59% |
| absolute effect | +6.12 п.п. |
| 95% CI | −6.58…+18.83 п.п. |
| p-value | 0.346 |
| observed / required sample | 217 / 478 |

Положительный point estimate не является достаточным основанием для rollout: доверительный
интервал пересекает ноль, а выборка меньше расчётной для MDE 12 п.п.

## Checks

- 25 Python data-quality checks: all `PASS`;
- 6 automated tests: all passed;
- Ruff lint and format: passed;
- PostgreSQL container: healthy;
- 14 SQL data-quality checks: all `PASS`;
- Python ↔ PostgreSQL reconciliation: 0 key and 0 metric mismatches;
- notebooks: executed top-to-bottom with no error outputs.
- Business Overview, Activation, Retention и Experiment: production build completed; desktop/mobile rendering,
  переключение вкладок и chart controls verified; browser console has no warnings or errors.

Все значения являются результатом симуляции и демонстрируют метод, а не реальные
показатели компании.
