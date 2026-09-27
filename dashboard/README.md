# DataLens dashboard contract

DataLens подключается к PostgreSQL analytics marts, а не к сырым CSV.

Week 1 source:

- `analytics.mart_user_activation`.

Следующие витрины:

- `analytics.mart_daily_connection_quality`;
- `analytics.mart_subscription_retention`;
- `analytics.mart_server_unit_economics`;
- `analytics.mart_experiment_readout`.

Публичная версия использует только synthetic data. Screenshots и описание фильтров
сохраняются как offline backup.
