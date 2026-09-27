# BI dashboard contract

BI-инструмент подключается к PostgreSQL analytics marts:

- `analytics.mart_monthly_business` — база, активность, churn, MRR, cash revenue, трафик;
- `analytics.mart_subscriber_activation` — путь от оплаты до использования через HAPP.

Минимальные страницы: **Business overview** и **New subscriber activation**. Публичная
версия использует только synthetic data; выполненный HTML-notebook служит offline backup.
