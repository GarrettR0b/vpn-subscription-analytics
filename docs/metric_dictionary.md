# Metric dictionary

## Eligible workspace

Новый trial workspace, созданный не internal/test actor. В synthetic MVP все строки
`core.workspaces` являются eligible; поле `is_internal` оставлено для явного фильтра.

## Knowledge base connected

Первое событие `knowledge_base_connected` в `core.product_events`.

## Teammate invited

Первое событие `teammate_invited`. Owner не считается teammate.

## Accepted AI suggestion

Строка `core.ai_suggestions` с непустым `accepted_at`. Отменённые или сгенерированные,
но не принятые suggestions не входят в numerator.

## 7-day activation rate

```text
activated eligible workspaces / all eligible new workspaces
```

Workspace активирован, если до `created_at + 7 days`:

- подключена knowledge base;
- приглашён teammate;
- принято не менее трёх suggestions;
- первое accepted suggestion произошло не раньше двух setup-событий.

Решение: найти step с наибольшим addressable drop-off и оценить guided onboarding.

## Time to first value

Количество часов от создания workspace до первого accepted suggestion. Метрика считается
только для workspace с принятым suggestion и показывается вместе с sample size.

## Guardrails для следующих этапов

- ticket reopen rate ≤7 days;
- p95 AI latency;
- inference cost per activated workspace;
- 14-day retained usage.
