from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import psycopg

from vpn_analytics.metrics import activation_experiment_statistics

MONTHLY_SQL = """
SELECT
    TO_CHAR(month_start, 'YYYY-MM') AS month,
    ending_paid_subscribers AS "endingPaidSubscribers",
    monthly_active_paid_users AS "monthlyActivePaidUsers",
    regular_paid_users AS "regularPaidUsers",
    basic_active_subscribers AS "basicActiveSubscribers",
    pro_active_subscribers AS "proActiveSubscribers",
    new_paid_users AS "newPaidUsers",
    churned_users AS "churnedUsers",
    cash_revenue_rub::FLOAT AS "cashRevenueRub",
    subscription_mrr_rub::FLOAT AS "subscriptionMrrRub",
    addon_mrr_rub::FLOAT AS "addonMrrRub",
    normalized_mrr_rub::FLOAT AS "mrrRub",
    extra_device_slots AS "extraDeviceSlots",
    connection_failure_rate::FLOAT AS "connectionFailureRate",
    traffic_gb::FLOAT AS "trafficGb"
FROM analytics.mart_monthly_business
ORDER BY month_start
"""

ACTIVATION_SUMMARY_SQL = """
SELECT
    COUNT(*) AS "eligibleSubscriptions",
    COUNT(*) FILTER (
        WHERE first_fetched_at < subscription_started_at + INTERVAL '7 days'
    ) AS "linkFetchedSubscriptions",
    COUNT(*) FILTER (
        WHERE first_fetched_at < subscription_started_at + INTERVAL '7 days'
          AND first_successful_connection_at < subscription_started_at + INTERVAL '7 days'
    ) AS "firstConnectedSubscriptions",
    COUNT(*) FILTER (WHERE activated_7d) AS "activatedSubscriptions",
    AVG(activated_7d::INT)::FLOAT AS "activationRate",
    AVG(COALESCE(
        first_fetched_at < subscription_started_at + INTERVAL '7 days', FALSE
    )::INT)::FLOAT
        AS "linkFetchRate",
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY time_to_first_value_hours) FILTER (
        WHERE time_to_first_value_hours IS NOT NULL
    )::FLOAT AS "medianTimeToValueHours",
    SUM(failed_attempts_7d)::FLOAT / NULLIF(SUM(total_attempts_7d), 0)
        AS "connectionFailureRate"
FROM analytics.mart_subscriber_activation
"""

ACTIVATION_FUNNEL_SQL = """
WITH flags AS (
    SELECT
        *,
        first_fetched_at < subscription_started_at + INTERVAL '7 days' AS link_ok,
        first_successful_connection_at < subscription_started_at + INTERVAL '7 days'
            AS first_connection_ok
    FROM analytics.mart_subscriber_activation
), funnel AS (
    SELECT 1 AS stage_order, 'Оплата' AS stage, COUNT(*) AS subscriptions FROM flags
    UNION ALL
    SELECT 2, 'Ссылка добавлена в HAPP', COUNT(*) FILTER (WHERE link_ok) FROM flags
    UNION ALL
    SELECT 3, 'Первое подключение', COUNT(*) FILTER (
        WHERE link_ok AND first_connection_ok
    ) FROM flags
    UNION ALL
    SELECT 4, 'Активация за 7 дней', COUNT(*) FILTER (WHERE activated_7d) FROM flags
)
SELECT
    stage_order AS "stageOrder",
    stage,
    subscriptions,
    subscriptions::FLOAT / FIRST_VALUE(subscriptions) OVER (ORDER BY stage_order)
        AS "conversionFromPurchase"
FROM funnel
ORDER BY stage_order
"""

ACTIVATION_MONTHLY_SQL = """
SELECT
    TO_CHAR(DATE_TRUNC('month', subscription_started_at), 'YYYY-MM') AS month,
    COUNT(*) AS "eligibleSubscriptions",
    COUNT(*) FILTER (WHERE activated_7d) AS "activatedSubscriptions",
    AVG(activated_7d::INT)::FLOAT AS "activationRate",
    AVG(COALESCE(
        first_fetched_at < subscription_started_at + INTERVAL '7 days', FALSE
    )::INT)::FLOAT
        AS "linkFetchRate",
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY time_to_first_value_hours) FILTER (
        WHERE time_to_first_value_hours IS NOT NULL
    )::FLOAT AS "medianTimeToValueHours"
FROM analytics.mart_subscriber_activation
GROUP BY 1
ORDER BY 1
"""

ACTIVATION_SEGMENTS_SQL = """
WITH segments AS (
    SELECT
        'Канал продажи' AS dimension,
        CASE sales_channel
            WHEN 'telegram_bot' THEN 'Telegram-бот'
            ELSE 'Сайт'
        END AS segment,
        activated_7d,
        first_fetched_at < subscription_started_at + INTERVAL '7 days' AS link_ok,
        time_to_first_value_hours,
        failed_attempts_7d,
        total_attempts_7d
    FROM analytics.mart_subscriber_activation
    UNION ALL
    SELECT
        'Тариф',
        CASE plan WHEN 'basic' THEN 'Базовая' ELSE 'Про' END,
        activated_7d,
        first_fetched_at < subscription_started_at + INTERVAL '7 days',
        time_to_first_value_hours,
        failed_attempts_7d,
        total_attempts_7d
    FROM analytics.mart_subscriber_activation
)
SELECT
    dimension,
    segment,
    COUNT(*) AS "eligibleSubscriptions",
    COUNT(*) FILTER (WHERE activated_7d) AS "activatedSubscriptions",
    AVG(activated_7d::INT)::FLOAT AS "activationRate",
    AVG(COALESCE(link_ok, FALSE)::INT)::FLOAT AS "linkFetchRate",
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY time_to_first_value_hours) FILTER (
        WHERE time_to_first_value_hours IS NOT NULL
    )::FLOAT AS "medianTimeToValueHours",
    SUM(failed_attempts_7d)::FLOAT / NULLIF(SUM(total_attempts_7d), 0)
        AS "connectionFailureRate"
FROM segments
GROUP BY dimension, segment
ORDER BY dimension, segment
"""

RETENTION_SUMMARY_SQL = """
SELECT
    month_number AS "monthNumber",
    'M' || month_number AS period,
    COUNT(*) AS "eligibleSubscriptions",
    COUNT(*) FILTER (WHERE retained) AS "retainedSubscriptions",
    AVG(retained::INT)::FLOAT AS "retentionRate"
FROM analytics.mart_subscriber_retention
GROUP BY month_number
ORDER BY month_number
"""

RETENTION_COHORTS_SQL = """
SELECT
    TO_CHAR(cohort_month, 'YYYY-MM') AS cohort,
    month_number AS "monthNumber",
    'M' || month_number AS period,
    COUNT(*) AS "cohortSize",
    COUNT(*) FILTER (WHERE retained) AS "retainedSubscriptions",
    AVG(retained::INT)::FLOAT AS "retentionRate"
FROM analytics.mart_subscriber_retention
GROUP BY cohort_month, month_number
ORDER BY cohort_month, month_number
"""

RETENTION_SEGMENTS_SQL = """
WITH m1 AS (
    SELECT *
    FROM analytics.mart_subscriber_retention
    WHERE month_number = 1
), segments AS (
    SELECT
        'Канал продажи' AS dimension,
        CASE sales_channel
            WHEN 'telegram_bot' THEN 'Telegram-бот'
            ELSE 'Сайт'
        END AS segment,
        retained
    FROM m1
    UNION ALL
    SELECT
        'Тариф',
        CASE plan WHEN 'basic' THEN 'Базовая' ELSE 'Про' END,
        retained
    FROM m1
    UNION ALL
    SELECT
        '7-day activation',
        CASE WHEN activated_7d THEN 'Активировались' ELSE 'Не активировались' END,
        retained
    FROM m1
)
SELECT
    dimension,
    segment,
    COUNT(*) AS "eligibleSubscriptions",
    COUNT(*) FILTER (WHERE retained) AS "retainedSubscriptions",
    AVG(retained::INT)::FLOAT AS "retentionRate"
FROM segments
GROUP BY dimension, segment
ORDER BY dimension, segment
"""

EXPERIMENT_ROWS_SQL = """
SELECT
    onboarding_variant,
    activated_7d
FROM analytics.mart_activation_experiment
ORDER BY subscription_id
"""

EXPERIMENT_VARIANTS_SQL = """
SELECT
    onboarding_variant AS variant,
    CASE onboarding_variant WHEN 'control' THEN 'Control' ELSE 'Treatment' END
        AS "variantLabel",
    COUNT(*) AS subscriptions,
    COUNT(*) FILTER (WHERE activated_7d) AS "activatedSubscriptions",
    AVG(activated_7d::INT)::FLOAT AS "activationRate",
    AVG(link_fetched_7d::INT)::FLOAT AS "linkFetchRate",
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY time_to_first_value_hours) FILTER (
        WHERE time_to_first_value_hours IS NOT NULL
    )::FLOAT AS "medianTimeToValueHours",
    SUM(failed_attempts_7d)::FLOAT / NULLIF(SUM(total_attempts_7d), 0)
        AS "connectionFailureRate"
FROM analytics.mart_activation_experiment
GROUP BY onboarding_variant
ORDER BY onboarding_variant
"""

EXPERIMENT_MONTHLY_SQL = """
SELECT
    TO_CHAR(DATE_TRUNC('month', subscription_started_at), 'YYYY-MM') AS month,
    onboarding_variant AS variant,
    CASE onboarding_variant WHEN 'control' THEN 'Control' ELSE 'Treatment' END
        AS "variantLabel",
    COUNT(*) AS subscriptions,
    AVG(activated_7d::INT)::FLOAT AS "activationRate"
FROM analytics.mart_activation_experiment
GROUP BY 1, onboarding_variant
ORDER BY 1, onboarding_variant
"""


def _arguments() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Create reviewed data for the VPN dashboard.")
    parser.add_argument(
        "--database-url",
        default=os.environ.get(
            "DATABASE_URL",
            "postgresql://analytics:analytics@127.0.0.1:5432/vpn_analytics",
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "data" / "generated" / "business_overview_snapshot.json",
    )
    parser.add_argument(
        "--build-status",
        choices=("creating", "updating", "paused", "complete"),
        default="complete",
    )
    return parser.parse_args()


def _rows(connection: psycopg.Connection, sql: str) -> list[dict[str, object]]:
    cursor = connection.execute(sql)
    columns = [column.name for column in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _source(label: str, sql: str, metric_definitions: list[dict[str, object]]) -> dict:
    return {
        "label": label,
        "sql": sql.strip(),
        "tables": ["analytics.mart_subscriber_activation"],
        "filters": ["Paid subscriptions with a complete seven-day observation window"],
        "executedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "evidenceFlow": [
            {
                "title": "PostgreSQL analytics mart",
                "detail": "Metrics use a reconciled subscription-level mart after SQL data-quality checks.",
            }
        ],
        "metricDefinitions": metric_definitions,
    }


def main() -> int:
    args = _arguments()
    generated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    with psycopg.connect(args.database_url) as connection:
        monthly_rows = _rows(connection, MONTHLY_SQL)
        activation_summary = _rows(connection, ACTIVATION_SUMMARY_SQL)
        activation_funnel = _rows(connection, ACTIVATION_FUNNEL_SQL)
        activation_monthly = _rows(connection, ACTIVATION_MONTHLY_SQL)
        activation_segments = _rows(connection, ACTIVATION_SEGMENTS_SQL)
        retention_summary = _rows(connection, RETENTION_SUMMARY_SQL)
        retention_cohorts = _rows(connection, RETENTION_COHORTS_SQL)
        retention_segments = _rows(connection, RETENTION_SEGMENTS_SQL)
        experiment_rows = _rows(connection, EXPERIMENT_ROWS_SQL)
        experiment_variants = _rows(connection, EXPERIMENT_VARIANTS_SQL)
        experiment_monthly = _rows(connection, EXPERIMENT_MONTHLY_SQL)

    experiment_summary = activation_experiment_statistics(experiment_rows)

    funnel_counts = [row["subscriptions"] for row in activation_funnel]
    assert funnel_counts == sorted(funnel_counts, reverse=True)
    assert activation_summary[0]["eligibleSubscriptions"] == funnel_counts[0]
    assert activation_summary[0]["activatedSubscriptions"] == funnel_counts[-1]
    assert retention_summary[0]["monthNumber"] == 0
    assert retention_summary[0]["retentionRate"] == 1
    assert all(0 <= row["retentionRate"] <= 1 for row in retention_summary)
    assert {row["variant"] for row in experiment_variants} == {"control", "treatment"}
    assert experiment_summary["observedSampleSize"] == sum(
        row["subscriptions"] for row in experiment_variants
    )

    activation_definitions = [
        {
            "label": "Eligible subscriptions",
            "definition": "New paid subscriptions with a complete seven-day observation window.",
            "componentIds": ["eligible-subscriptions", "activation-funnel", "activation-detail"],
            "sourceLineage": [{"tables": ["analytics.mart_subscriber_activation"]}],
        },
        {
            "label": "7-day activation",
            "definition": "The HAPP link was fetched, at least three successful proxy sessions occurred on two or more UTC days, and protected traffic reached 30 minutes within seven days of subscription start.",
            "formula": "activated subscriptions / eligible subscriptions",
            "componentIds": [
                "activation-rate",
                "activation-trend",
                "activation-by-channel",
                "activation-by-plan",
                "activation-detail",
            ],
            "sourceLineage": [{"tables": ["analytics.mart_subscriber_activation"]}],
        },
    ]
    retention_definitions = [
        {
            "label": "Cohort baseline",
            "definition": "M0 contains every eligible new paid subscription in its purchase month and is fixed at 100%.",
            "componentIds": ["retention-curve", "retention-detail"],
            "sourceLineage": [{"tables": ["analytics.mart_subscriber_retention"]}],
        },
        {
            "label": "Monthly usage retention",
            "definition": "Share of an eligible paid cohort with at least one successful proxy session in the complete calendar month at the stated age.",
            "formula": "retained subscriptions / eligible subscriptions",
            "componentIds": [
                "m1-retention",
                "m2-retention",
                "m3-retention",
                "retention-curve",
                "retention-by-channel",
                "retention-by-plan",
                "retention-by-activation",
                "retention-detail",
            ],
            "sourceLineage": [{"tables": ["analytics.mart_subscriber_retention"]}],
        },
    ]
    experiment_definitions = [
        {
            "label": "Experiment population",
            "definition": "New paid subscriptions randomly assigned after purchase to the standard link flow or a guided HAPP setup reminder, with a complete seven-day observation window.",
            "componentIds": ["experiment-sample", "experiment-activation", "experiment-detail"],
            "sourceLineage": [{"tables": ["analytics.mart_activation_experiment"]}],
        },
        {
            "label": "Experiment effect",
            "definition": "Treatment activation rate minus control activation rate; uncertainty is a two-sided 95% confidence interval from the unpooled standard error.",
            "formula": "treatment activation rate - control activation rate",
            "componentIds": ["experiment-effect", "experiment-activation"],
            "sourceLineage": [{"tables": ["analytics.mart_activation_experiment"]}],
        },
        {
            "label": "Statistical test",
            "definition": "Two-sided two-proportion z-test with alpha 0.05. Planning uses 80% power and a minimum detectable effect of 12 percentage points.",
            "componentIds": ["experiment-p-value", "experiment-detail"],
            "sourceLineage": [{"tables": ["analytics.mart_activation_experiment"]}],
        },
    ]
    snapshot = {
        "surface": "dashboard",
        "title": "VPN Analytics — подписка через HAPP",
        "generatedAt": generated_at,
        "status": "synthetic",
        "buildStatus": args.build_status,
        "filters": [],
        "queries": {
            "monthly_business": {
                "rows": monthly_rows,
                "source": {
                    "label": "Synthetic PostgreSQL mart: monthly business",
                    "sql": MONTHLY_SQL.strip(),
                    "tables": ["analytics.mart_monthly_business"],
                    "filters": ["Complete UTC calendar months: January–June 2026"],
                    "executedAt": generated_at,
                    "evidenceFlow": [
                        {
                            "title": "PostgreSQL mart",
                            "detail": "The dashboard reads the reconciled monthly business mart after SQL data-quality checks.",
                        }
                    ],
                    "metricDefinitions": [
                        {
                            "label": "Active paid subscribers",
                            "definition": "Distinct paid subscribers active at the end of the calendar month.",
                            "componentIds": ["active-paid", "subscriber-trend", "monthly-detail"],
                            "sourceLineage": [{"tables": ["analytics.mart_monthly_business"]}],
                        },
                        {
                            "label": "MRR",
                            "definition": "Monthly tariff revenue plus recurring revenue from additional device slots for subscriptions active at month end.",
                            "formula": "subscriptionMrrRub + addonMrrRub",
                            "componentIds": ["mrr", "mrr-mix", "monthly-detail"],
                            "sourceLineage": [{"tables": ["analytics.mart_monthly_business"]}],
                        },
                        {
                            "label": "Cash revenue",
                            "definition": "Successful payments received during the calendar month.",
                            "componentIds": ["cash-revenue", "revenue-trend", "monthly-detail"],
                            "sourceLineage": [{"tables": ["analytics.mart_monthly_business"]}],
                        },
                        {
                            "label": "Connection failure rate",
                            "definition": "Failed proxy connection attempts divided by all proxy connection attempts in the month.",
                            "componentIds": ["failure-rate", "quality-trend", "monthly-detail"],
                            "sourceLineage": [{"tables": ["analytics.mart_monthly_business"]}],
                        },
                    ],
                },
            },
            "activation_summary": {
                "rows": activation_summary,
                "source": _source(
                    "Synthetic PostgreSQL mart: activation summary",
                    ACTIVATION_SUMMARY_SQL,
                    activation_definitions,
                ),
            },
            "activation_funnel": {
                "rows": activation_funnel,
                "source": _source(
                    "Synthetic PostgreSQL mart: cumulative activation funnel",
                    ACTIVATION_FUNNEL_SQL,
                    activation_definitions,
                ),
            },
            "activation_monthly": {
                "rows": activation_monthly,
                "source": _source(
                    "Synthetic PostgreSQL mart: monthly activation cohorts",
                    ACTIVATION_MONTHLY_SQL,
                    activation_definitions,
                ),
            },
            "activation_segments": {
                "rows": activation_segments,
                "source": _source(
                    "Synthetic PostgreSQL mart: activation segments",
                    ACTIVATION_SEGMENTS_SQL,
                    activation_definitions,
                ),
            },
            "retention_summary": {
                "rows": retention_summary,
                "source": {
                    **_source(
                        "Synthetic PostgreSQL mart: weighted retention by cohort age",
                        RETENTION_SUMMARY_SQL,
                        retention_definitions,
                    ),
                    "tables": ["analytics.mart_subscriber_retention"],
                    "filters": ["Eligible new paid subscriptions; complete calendar months only"],
                },
            },
            "retention_cohorts": {
                "rows": retention_cohorts,
                "source": {
                    **_source(
                        "Synthetic PostgreSQL mart: retention cohorts",
                        RETENTION_COHORTS_SQL,
                        retention_definitions,
                    ),
                    "tables": ["analytics.mart_subscriber_retention"],
                    "filters": ["Eligible new paid subscriptions; complete calendar months only"],
                },
            },
            "retention_segments": {
                "rows": retention_segments,
                "source": {
                    **_source(
                        "Synthetic PostgreSQL mart: M1 retention segments",
                        RETENTION_SEGMENTS_SQL,
                        retention_definitions,
                    ),
                    "tables": ["analytics.mart_subscriber_retention"],
                    "filters": ["Month-one observations only"],
                },
            },
            "experiment_summary": {
                "rows": [experiment_summary],
                "methods": [
                    {
                        "language": "Python standard library",
                        "code": "Two-sided pooled two-proportion z-test; unpooled 95% CI for treatment minus control; normal-approximation sample-size planning for alpha=0.05, power=0.80 and MDE=12 p.p.",
                    }
                ],
                "source": {
                    **_source(
                        "Synthetic randomized onboarding experiment",
                        EXPERIMENT_ROWS_SQL,
                        experiment_definitions,
                    ),
                    "tables": ["analytics.mart_activation_experiment"],
                    "filters": [
                        "Control and treatment assignments with complete seven-day windows"
                    ],
                },
            },
            "experiment_variants": {
                "rows": experiment_variants,
                "source": {
                    **_source(
                        "Synthetic experiment results by variant",
                        EXPERIMENT_VARIANTS_SQL,
                        experiment_definitions,
                    ),
                    "tables": ["analytics.mart_activation_experiment"],
                    "filters": [
                        "Control and treatment assignments with complete seven-day windows"
                    ],
                },
            },
            "experiment_monthly": {
                "rows": experiment_monthly,
                "source": {
                    **_source(
                        "Synthetic experiment activation by purchase month",
                        EXPERIMENT_MONTHLY_SQL,
                        experiment_definitions,
                    ),
                    "tables": ["analytics.mart_activation_experiment"],
                    "filters": [
                        "Control and treatment assignments with complete seven-day windows"
                    ],
                },
            },
            "tariff_terms": {
                "rows": [
                    {
                        "plan": "Базовая",
                        "monthlyPriceRub": 130,
                        "includedDevices": 6,
                        "freeTrialDays": 4,
                    },
                    {
                        "plan": "Про",
                        "monthlyPriceRub": 220,
                        "includedDevices": 8,
                        "freeTrialDays": 4,
                    },
                    {
                        "plan": "Доп. устройство",
                        "monthlyPriceRub": 30,
                        "includedDevices": 1,
                        "freeTrialDays": None,
                    },
                ],
                "source": {
                    "label": "Tariff assumptions for the synthetic portfolio model",
                    "files": ["docs/business_problem.md", "docs/metric_dictionary.md"],
                    "evidenceFlow": [
                        {
                            "title": "User-provided terms",
                            "detail": "A time-limited four-day free trial is available before purchase; Basic costs 130 RUB/month for six devices and Pro costs 220 RUB/month for eight devices.",
                        },
                        {
                            "title": "Synthetic assumption",
                            "detail": "One additional device slot costs 30 RUB/month and can be changed in the generator constant.",
                        },
                    ],
                    "metricDefinitions": [
                        {
                            "label": "Free trial",
                            "definition": "A time-limited four-day trial available before a paid subscription starts; trial users are excluded from paid subscription, revenue and post-purchase activation metrics.",
                            "componentIds": ["tariff-terms"],
                            "sourceLineage": [
                                {
                                    "files": [
                                        "docs/business_problem.md",
                                        "docs/metric_dictionary.md",
                                    ]
                                }
                            ],
                        }
                    ],
                },
            },
        },
    }
    if args.output.exists():
        existing = json.loads(args.output.read_text(encoding="utf-8"))
        if "id" in existing:
            snapshot["id"] = existing["id"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
