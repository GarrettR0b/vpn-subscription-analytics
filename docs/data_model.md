# Data model

## Core grains

| Table | Grain | Primary key |
|---|---|---|
| `core.users` | одна строка на зарегистрированного пользователя | `user_id` |
| `core.devices` | одна строка на устройство пользователя | `device_id` |
| `core.subscriptions` | одна строка на подписку MVP | `subscription_id` |
| `core.product_events` | одна строка на product event | `event_id` |
| `core.vpn_servers` | одна строка на VPN-сервер | `server_id` |
| `core.vpn_sessions` | одна строка на попытку VPN-подключения | `vpn_session_id` |
| `core.experiment_assignments` | одна строка на experiment × user | составной PK |

## Analytics grain

`analytics.mart_user_activation` содержит одну строку на eligible user: onboarding
milestones, успешные сессии в days 0–7, active days, protected minutes, time-to-value,
activation flag и experiment variant.

## Relationships

```text
users 1 ── * devices 1 ── * vpn_sessions * ── 1 vpn_servers
users 1 ── 1 subscriptions
users 1 ── * product_events
users 1 ── * experiment_assignments
```
