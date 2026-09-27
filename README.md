# Аналитическая система VPN-сервиса: подписки, активация и качество соединений

Портфолио-проект Data/BI Analyst: от синтетических событий подписочного VPN-сервиса до
PostgreSQL-витрин, воспроизводимого Python-анализа, A/B-теста и Yandex DataLens.

> Проект является обезличенной реконструкцией типа коммерческой аналитической задачи,
> над которой автор работал профессионально. Названия, данные, параметры и результаты
> полностью синтетические и не содержат конфиденциальной информации компании.

## Business problem

Синтетический сервис `ShieldRoute` продаёт месячные и годовые VPN-подписки. Пользователи
регистрируются, устанавливают приложение, выбирают сервер и запускают защищённые сессии.
Не все новые пользователи получают ценность в первые дни, а рост трафика увеличивает
инфраструктурные расходы.

Главный вопрос:

> Какие действия в первые 7 дней приводят пользователя к регулярному использованию VPN и
> конверсии в оплату, не ухудшая качество соединения и unit economics?

## Что реализовано

- контракт бизнес-задачи, KPI и guardrails;
- PostgreSQL core model для пользователей, устройств, серверов, сессий и подписок;
- детерминированный генератор связанных synthetic CSV;
- Python loader для PostgreSQL;
- витрина `analytics.mart_user_activation`;
- SQL- и Python-проверки качества данных;
- выполненный notebook и автономная HTML-версия;
- Docker Compose для локальной базы.

## Быстрый старт

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[analysis,dev]"

python -m vpn_analytics.generator --profile small --sample-dir data/samples
python -m vpn_analytics.data_quality --input-dir data/generated

docker compose up -d postgres
python -m vpn_analytics.loader --input-dir data/generated
python scripts/create_starter_notebook.py
python -m pytest
```

Подключение PostgreSQL по умолчанию:

```text
postgresql://analytics:analytics@localhost:5433/vpn_analytics
```

## Week 1 vertical slice

```text
Python generator → CSV → PostgreSQL core tables
                 → analytics.mart_user_activation
                 → Python notebook / будущий DataLens
```

## Metric contract

Пользователь достигает `7-day activation`, если в первые семь дней:

1. приложение установлено и произошло успешное VPN-подключение;
2. выполнено не менее трёх успешных VPN-сессий;
3. сессии проходили минимум в два разных календарных дня;
4. суммарное время под защитой составило не менее 30 минут.

Определения и guardrails: [docs/metric_dictionary.md](docs/metric_dictionary.md).

Последний воспроизводимый прогон: [docs/validation.md](docs/validation.md).

## Структура

```text
config/       параметры генерации
data/         generated data и небольшие samples
docs/         бизнес-контекст, модель данных и KPI
notebooks/    воспроизводимый анализ activation funnel
scripts/      локальные команды подготовки артефактов
sql/ddl/      схема PostgreSQL
sql/marts/    аналитические витрины
sql/checks/   проверки качества
src/          генератор, loader, метрики и Python QA
tests/        автоматические тесты
dashboard/    спецификация DataLens и offline screenshots
excel/        будущая модель unit economics
```

## Ограничения

- Все числа являются результатом симуляции, а не показателями реальной компании.
- Успешная VPN-сессия — proxy полученной ценности, но не гарантия удовлетворённости.
- Наблюдательная связь между активацией и оплатой не доказывает причинность.
- Экспериментальные результаты предназначены для демонстрации ITT-подхода.
