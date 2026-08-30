# Data model

## Core grains

| Таблица | Grain | Primary key |
|---|---|---|
| `core.workspaces` | одна строка на workspace | `workspace_id` |
| `core.users` | одна строка на user | `user_id` |
| `core.subscriptions` | одна строка на trial/subscription lifecycle MVP | `subscription_id` |
| `core.product_events` | одна строка на событие | `event_id` |
| `core.tickets` | одна строка на support ticket | `ticket_id` |
| `core.ai_suggestions` | одна строка на AI suggestion | `suggestion_id` |
| `core.experiment_assignments` | одна строка на experiment × workspace | составной PK |

## Week 1 analytical grain

`analytics.mart_workspace_activation` содержит одну строку на workspace. В ней хранятся
первые timestamps onboarding, принятые suggestions в days 0–7, activation flag и
time-to-first-value.

## Связи

```text
workspaces 1 ── * users
workspaces 1 ── * product_events
workspaces 1 ── * tickets 1 ── * ai_suggestions
workspaces 1 ── 1 subscriptions (MVP)
workspaces 1 ── * experiment_assignments
users      1 ── * product_events / ai_suggestions
```
