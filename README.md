# Аналитическая система AI SaaS: витрины данных, продуктовые метрики и BI

Портфолио-проект Data/BI Analyst: от синтетических событий B2B SaaS до PostgreSQL-витрин,
воспроизводимого Python-анализа, A/B-теста и Yandex DataLens.

> Проект является обезличенной реконструкцией типа коммерческой аналитической задачи,
> над которой автор работал профессионально. Названия, данные, параметры и результаты
> полностью синтетические и не содержат конфиденциальной информации компании.

## Business problem

Небольшой сервис `AnswerFlow` помогает командам поддержки создавать ответы клиентам с
помощью AI и базы знаний. Регистрации растут, но не все workspace доходят до регулярной
ценности, а inference cost может расти быстрее подписочной выручки.

Главный вопрос:

> Какие действия в первые 7 дней приводят workspace к устойчивой ценности и как повысить
> activation, не ухудшив качество поддержки и unit economics?

## Что уже реализовано

- контракт бизнес-задачи и метрик;
- PostgreSQL core model;
- детерминированный генератор связанных CSV;
- Python loader для PostgreSQL;
- первая аналитическая витрина `analytics.mart_workspace_activation`;
- SQL- и Python-проверки качества данных;
- starter notebook для проверки данных и activation;
- Docker Compose для локальной базы.

## Быстрый старт

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[analysis,dev]"

python -m ai_saas_analytics.generator --profile small --sample-dir data/samples
python -m ai_saas_analytics.data_quality --input-dir data/generated

docker compose up -d postgres
python -m ai_saas_analytics.loader --input-dir data/generated
python scripts/create_starter_notebook.py
python -m pytest
```

Подключение PostgreSQL по умолчанию:

```text
postgresql://analytics:analytics@localhost:5433/ai_saas
```

## Week 1 vertical slice

```text
Python generator
    ↓ CSV
PostgreSQL core tables
    ↓ SQL business logic
analytics.mart_workspace_activation
    ↓
Python notebook / будущий DataLens
```

## Metric contract

`7-day activation` достигается, если workspace в первые семь дней:

1. подключил базу знаний;
2. пригласил как минимум одного teammate;
3. принял минимум три AI suggestions;
4. первое принятие произошло после подключения базы и приглашения teammate.

Определения и ограничения: [docs/metric_dictionary.md](docs/metric_dictionary.md).

Результат последнего воспроизводимого прогона: [docs/validation.md](docs/validation.md).

## Структура

```text
config/       параметры генерации
data/         generated data и небольшие samples
docs/         бизнес-контекст, модель данных и метрики
notebooks/    воспроизводимый анализ
scripts/      локальные команды подготовки артефактов
sql/ddl/      схема PostgreSQL
sql/marts/    аналитические витрины
sql/checks/   проверки качества
src/          генератор, loader и Python QA
tests/        автоматические тесты
dashboard/    спецификация и screenshots DataLens
```

## Ограничения

- Все числа являются результатом симуляции, а не показателями реальной компании.
- Acceptance и reopen rate — proxies качества ответа.
- Наблюдательные связи между onboarding и retention не доказывают причинность.
- Эффект эксперимента будет анализироваться отдельно по ITT после реализации Week 3.
