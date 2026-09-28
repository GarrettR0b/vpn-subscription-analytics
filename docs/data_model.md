# Data model

## Core grains

| Table | Grain | Primary key |
|---|---|---|
| `core.dataset_periods` | один период синтетического наблюдения | `dataset_id` |
| `core.users` | один пользователь | `user_id` |
| `core.subscriptions` | одна приобретённая подписка | `subscription_id` |
| `core.subscription_links` | одна персональная ссылка подписки | `subscription_link_id` |
| `core.payments` | одна попытка оплаты | `payment_id` |
| `core.proxy_servers` | один прокси-сервер | `server_id` |
| `core.proxy_sessions` | одна попытка подключения | `proxy_session_id` |

## Analytics grains

- `analytics.mart_subscriber_activation` — одна новая оплаченная подписка с полным
  семидневным окном наблюдения;
- `analytics.mart_monthly_business` — один полный календарный месяц.
- `analytics.mart_subscriber_retention` — одна eligible-подписка × один полный
  календарный месяц жизни когорты.
- `analytics.mart_activation_experiment` — одна eligible-подписка, случайно назначенная
  в control или treatment постоплатного онбординга.

`core.subscriptions.onboarding_variant` хранит назначение эксперимента: постоянные
пользователи имеют `not_enrolled`, новые покупки — `control` или `treatment`.

## Relationships

```text
users 1 ── * subscriptions 1 ── 1 subscription_links
                         ├── * payments
                         └── * proxy_sessions * ── 1 proxy_servers
```

Собственного приложения и device-level событий нет. Факт загрузки ссылки приходит из
лога подписочного endpoint, факт использования — из прокси-сессий.
