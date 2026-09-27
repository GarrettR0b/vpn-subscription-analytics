# Metric dictionary

## Eligible user

Новый пользователь, который не является internal/test actor и имеет полное семидневное
окно наблюдения. Генератор создаёт пользователей минимум за 14 дней до конца периода.

## Successful VPN session

Строка `core.vpn_sessions` со `connection_status = 'success'`, непустым `ended_at` и
положительной длительностью. Неуспешные попытки остаются в denominator quality metrics.

## 7-day activation — primary KPI

```text
activated eligible users / all eligible new users
```

Пользователь активирован, если до `registered_at + 7 days`:

- приложение установлено;
- произошло минимум три успешных VPN-сессии;
- успешные сессии были минимум в два разных UTC-дня;
- суммарное защищённое время составило не менее 30 минут.

Метрика отражает не разовый технический тест, а повторное получение ценности. Порог
является портфолио-допущением и в реальной компании должен калиброваться по retention.

## Driver metrics

- install rate within 24h;
- first connection success rate within 24h;
- median time to first successful connection;
- share with a successful connection on 2+ days in week 1.

## Guardrails

- connection failure rate;
- p95 successful connection time, ms;
- forced disconnect rate;
- infrastructure cost per protected GB (следующий этап).

## Paid conversion

Доля eligible users с непустым `converted_at` в `core.subscriptions`. Показывается по
activation cohort, plan и acquisition channel; не считается причинным эффектом activation.

## Experiment

`smart_location_onboarding_v1` сравнивает control и treatment на уровне user по ITT.
Primary KPI — 7-day activation; guardrails — failure rate и p95 connection time.
